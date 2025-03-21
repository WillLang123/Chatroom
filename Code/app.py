from flask import Flask, render_template, jsonify, request, session, Response
import secrets
import json
import time
from database import initDB, getDBConnection, createMessageTable
from chatroom import createChatroom, joinChatroom, deleteChatroom, getChatroomByID

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
        conn = getDBConnection()
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
        conn = getDBConnection()
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
        conn = getDBConnection()
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
    response, status = createChatroom(data.get('name'), session['userID'])
    return jsonify(response), status

@app.route('/joinChatroom', methods=['POST'])
def handleJoinChatroom():
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    data = request.get_json()
    response, status = joinChatroom(data.get('chatroomID'), session['userID'])
    return jsonify(response), status

@app.route('/deleteChatroom/<int:chatroomID>', methods=['DELETE'])
def handleDeleteChatroom(chatroomID):
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    response, status = deleteChatroom(chatroomID, session['userID'])
    return jsonify(response), status

@app.route('/chatroom/<int:chatroomID>/messages')
def getChatroomMessages(chatroomID):
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    try:
        conn = getDBConnection()
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
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    data = request.get_json()
    message = data.get('message')
    if not message or not message.strip():
        return jsonify({'status': 'error', 'message': 'Message cannot be empty'}), 400
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        createMessageTable(chatroomID)
        cursor.execute(f'''INSERT INTO messages_{chatroomID} (userID, message) VALUES (?, ?)''', (session['userID'], message.strip()))
        messageID = cursor.lastrowid
        cursor.execute('SELECT username FROM users WHERE id = ?', (session['userID'],))
        username = cursor.fetchone()[0]
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
    if 'userID' not in session:
        return 'Not logged in', 401
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        return 'Not authorized', 403
    def generate():
        lastID = 0
        while True:
            try:
                conn = getDBConnection()
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
    initDB()
    app.run(host='0.0.0.0', port=3000, debug=True)
