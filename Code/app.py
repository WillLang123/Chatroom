from flask import Flask, render_template, jsonify, request, session, Response
import secrets
import json
import time
import sqlite3
from utils import createMessageTable, getChatroomByID

app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(32)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password are required'}), 400
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Username already exists'}), 400
        cursor.execute('INSERT INTO users (username, password, chatroomIDs) VALUES (?, ?, ?)', (username, password, ''))
        userID = cursor.lastrowid
        conn.commit()
        session['userID'] = userID
        session['username'] = username
        return jsonify({'status': 'success', 'user': {'id': userID, 'username': username}}), 200
    except Exception as e:
        print(f"Error registering user: {str(e)}")
        conn.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to register user'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username, password = data.get('username'), data.get('password')
    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and password are required'}), 400
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401
        if password != user[2]:
            return jsonify({'status': 'error', 'message': 'Invalid username or password'}), 401
        session['userID'] = user[0]
        session['username'] = user[1]
        return jsonify({'status': 'success', 'user': {'id': user[0], 'username': user[1]}}), 200
    except Exception as e:
        print(f"Error logging in user: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to log in'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        print(f"Error logging out user: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to log out'}), 500

@app.route('/checkLogin', methods=['GET'])
def checkLogin():
    try:
        if 'userID' in session:
            return jsonify({'status': 'success', 'user': {'id': session['userID'], 'username': session['username']}}), 200
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    except Exception as e:
        print(f"Error checking auth: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to check auth'}), 500

@app.route('/chatrooms', methods=['GET'])
def getChatrooms():
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (session['userID'],))
        result = cursor.fetchone()
        if not result or not result[0]:
            return jsonify({'status': 'success', 'chatrooms': []}), 200
        chatroomIDs = [int(id) for id in result[0].split(',')]
        chatrooms = []
        for chatroomID in chatroomIDs:
            cursor.execute('SELECT id, name, adminID FROM chatrooms WHERE id = ?', (chatroomID,))
            chatroom = cursor.fetchone()
            if chatroom:
                chatrooms.append({
                    'id': chatroom[0],
                    'name': chatroom[1],
                    'isAdmin': chatroom[2] == session['userID']
                })
        return jsonify({'status': 'success', 'chatrooms': chatrooms}), 200
    except Exception as e:
        print(f"Error getting user chatrooms: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to get chatrooms'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/createChatroom', methods=['POST'])
def handleCreateChatroom():
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'status': 'error', 'message': 'Chatroom name is required'}), 400
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO chatrooms (name, adminID) VALUES (?, ?)', (name, session['userID']))
        chatroomID = cursor.lastrowid
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (session['userID'],))
        result = cursor.fetchone()
        chatroomIDs = result[0].split(',') if result[0] else []
        chatroomIDs.append(str(chatroomID))
        cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', (','.join(chatroomIDs), session['userID']))
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS messages_{chatroomID} (id INTEGER PRIMARY KEY AUTOINCREMENT,userID INTEGER NOT NULL,message TEXT NOT NULL,timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        return jsonify({'status': 'success', 'chatroom': {'id': chatroomID,'name': name,'isAdmin': True}}), 200
    except Exception as e:
        print(f"Error creating chatroom: {str(e)}")
        conn.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to create chatroom'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/joinChatroom', methods=['POST'])
def handleJoinChatroom():
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    data = request.get_json()
    chatroomID = data.get('chatroomID')
    if not chatroomID:
        return jsonify({'status': 'error', 'message': 'Chatroom ID is required'}), 400
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name, adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        chatroom = cursor.fetchone()
        if not chatroom:
            return jsonify({'status': 'error', 'message': 'Chatroom not found'}), 404
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (session['userID'],))
        result = cursor.fetchone()
        chatroomIDs = result[0].split(',') if result[0] else []
        if str(chatroomID) in chatroomIDs:
            return jsonify({'status': 'error', 'message': 'Already in chatroom'}), 400
        chatroomIDs.append(str(chatroomID))
        cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', (','.join(chatroomIDs), session['userID']))
        conn.commit()
        return jsonify({'status': 'success', 'chatroom': {'id': chatroomID,'name': chatroom[0],'isAdmin': chatroom[1] == session['userID']}}), 200
    except Exception as e:
        print(f"Error joining chatroom: {str(e)}")
        conn.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to join chatroom'}), 500
    finally:
        cursor.close()
        conn.close()

# When called to delete chatroom using curl
@app.route('/deleteChatroom/<int:chatroomID>', methods=['DELETE'])
def handleDeleteChatroom(chatroomID):
    #checks to make sure a user is able to be compared before trying
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    try:
        #connects to the database and fetches admin id from chatroom table
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('SELECT adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        result = cursor.fetchone()
        #checks if there is an admin at all aka is there a chatroom
        if not result:
            return jsonify({'status': 'error', 'message': 'Chatroom not found'}), 404
        #checks if the user in session is an admin
        if result[0] != session['userID']:
            return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
        # begins to begins to iterate through every user in the database in that chatroom and removes the respective chatroom from the list
        cursor.execute('SELECT id, chatroomIDs FROM users')
        users = cursor.fetchall()
        for user in users:
            if user[1]:
                chatroomIDs = user[1].split(',')
                if str(chatroomID) in chatroomIDs:
                    chatroomIDs.remove(str(chatroomID))
                    newChatroomIDs = ','.join(chatroomIDs) if chatroomIDs else None
                    cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', (newChatroomIDs, user[0]))
        #tries to delete the database table for the chatroom's messages
        try:
            cursor.execute(f'DROP TABLE IF EXISTS messages_{chatroomID}')
        except Exception as e:
            print(f"Error dropping message table: {str(e)}")
        #finally removes the chatroom from the chatrooms database
        cursor.execute('DELETE FROM chatrooms WHERE id = ?', (chatroomID,))
        cursor.execute('COMMIT')
        return jsonify({'status': 'success'}), 200
    except Exception as e:
        #undoes changes if it messes up somehow
        print(f"Error deleting chatroom: {str(e)}")
        cursor.execute('ROLLBACK')
        return jsonify({'status': 'error', 'message': 'Failed to delete chatroom'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/chatroom/<int:chatroomID>/messages')
def getChatroomMessages(chatroomID):
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    try:
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        createMessageTable(chatroomID)
        cursor.execute(f'''SELECT m.id, m.userID, u.username, m.message, m.timestamp FROM messages_{chatroomID} m JOIN users u ON m.userID = u.id ORDER BY m.timestamp DESC LIMIT 50''')
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'userID': row[1],
                'username': row[2],
                'message': row[3],
                'timestamp': row[4]
            })
        return jsonify({'status': 'success', 'messages': messages[::-1]}), 200
    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        return jsonify({'status': 'success', 'messages': []}), 200
    finally:
        cursor.close()
        conn.close()

@app.route('/chatroom/<int:chatroomID>/send', methods=['POST'])
def handleSendMessage(chatroomID):
    # checks if user is logged in
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    chatroom = getChatroomByID(chatroomID)
    # checks if user is in the chatroom
    if not chatroom or session['userID'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    # grabs the json data, gets the message part, and check if its empty
    data = request.get_json()
    message = data.get('message')
    if not message or not message.strip():
        return jsonify({'status': 'error', 'message': 'Message cannot be empty'}), 400
    try:
        # tries to open database and put message in database
        conn = sqlite3.connect('chatroom.db')
        cursor = conn.cursor()
        createMessageTable(chatroomID)
        cursor.execute(f'''INSERT INTO messages_{chatroomID} (userID, message) VALUES (?, ?)''', (session['userID'], message.strip()))
        messageID = cursor.lastrowid
        # gets user from user database using the user id for message database
        cursor.execute('SELECT username FROM users WHERE id = ?', (session['userID'],))
        username = cursor.fetchone()[0]
        # pushes message and return feedback
        conn.commit()
        return jsonify({'status': 'success', 'message': {
            'id': messageID,
            'userID': session['userID'],
            'username': username,
            'message': message.strip(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }}), 200
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        conn.rollback()
        return jsonify({'status': 'error', 'message': 'Failed to send message'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/chatroom/<int:chatroomID>/stream')
def streamMessages(chatroomID):
    # checks if user is logged in
    if 'userID' not in session:
        return 'Not logged in', 401
    chatroom = getChatroomByID(chatroomID)
    # checks if user is in chatroom
    if not chatroom or session['userID'] not in chatroom['users']:
        return 'Not authorized', 403
    def generate():
        lastID = 0
        while True:
            try:
                #continuous tries to get ****
                conn = sqlite3.connect('chatroom.db')
                cursor = conn.cursor()
                createMessageTable(chatroomID)
                cursor.execute(f'''SELECT m.id, m.userID, u.username, m.message, m.timestamp FROM messages_{chatroomID} m JOIN users u ON m.userID = u.id WHERE m.id > ? ORDER BY m.timestamp ASC''', (lastID,))
                messages = cursor.fetchall()
                if messages:
                    for message in messages:
                        lastID = message[0]
                        data = {
                            'id': message[0],
                            'userID': message[1],
                            'username': message[2],
                            'message': message[3],
                            'timestamp': message[4]
                        }
                        yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:
                print(f"Error in message stream: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                cursor.close()
                conn.close()
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    conn = sqlite3.connect('chatroom.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,chatroomIDs TEXT DEFAULT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS chatrooms (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,adminID INTEGER NOT NULL,FOREIGN KEY (adminID) REFERENCES users (id))''')
        conn.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
    app.run(host='0.0.0.0', port=3000, debug=True)
