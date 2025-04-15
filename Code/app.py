from flask import Flask, render_template, jsonify, request, session, Response
import json
import time
from utils import quickCursor, quickClose, createMessageTable, getChatroomByID

app = Flask(__name__)
app.secret_key = "COSC4360GP"

#remove parameter function
@app.route('/')
def index():
    return render_template('mainPage.html')

@app.route("/register", methods=["POST"])
def register():
    dataFromAPI = request.get_json()
    username, password = dataFromAPI.get('username'), dataFromAPI.get('password')
    if not username or not password:
        error = jsonify({"problem": "Username and password are required"})
        return error
    try:
        cursor, conn = quickCursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            error = jsonify({"problem": "Username already exists"})
            return error
        cursor.execute('INSERT INTO users (username, password, chatroomIDs) VALUES (?, ?, ?)', (username, password, ''))
        userID = cursor.lastrowid
        conn.commit()
        session['userID'] = userID
        session['username'] = username
        meessageToAPI = jsonify({"signal": "ok", "user": {"id": userID, "username": username}})
        return meessageToAPI
    except Exception:
        print("Issue with registering user")
        conn.rollback()
        error = jsonify({"problem": "Failed to register user"})
        return error
    finally:
        quickClose(cursor,conn)

@app.route("/login", methods=["POST"])
def login():
    dataFromAPI = request.get_json()
    username, password = dataFromAPI.get('username'), dataFromAPI.get('password')
    if not username or not password:
        error = jsonify({"problem": "Username and password are required"})
        return error
    try:
        cursor, conn = quickCursor()
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if not user:
            error = jsonify({"problem": "Invalid username or password"})
            return error
        if password != user[2]:
            error = jsonify({"problem": "Invalid username or password"})
            return error
        session['userID'] = user[0]
        session['username'] = user[1]
        messageToAPI = jsonify({"signal": "ok", "user": {"id": user[0], "username": user[1]}})
        return messageToAPI
    except Exception:
        print("Issue with logging in user")
        error = jsonify({"problem": "Failed to log in"})
        return error
    finally:
        quickClose(cursor,conn)

@app.route("/logout", methods=["POST"])
def logout():
    try:
        session.clear()
        messageToAPI = jsonify({"signal": "ok"})
        return messageToAPI
    except Exception:
        print("Issue with logging out user")
        error = jsonify({"problem": "Failed to log out"})
        return error

@app.route("/checkLogin", methods=["GET"])
def checkLogin():
    try:
        if 'userID' in session:
            messageToAPI = jsonify({"signal": "ok", "user": {"id": session["userID"], "username": session["username"]}})
            return messageToAPI
        error = jsonify({"problem": "Not logged in"})
        return error
    except Exception:
        print("Issue with checking auth")
        error =jsonify({"problem": "Failed to check auth"})
        return error

@app.route("/chatrooms", methods=["GET"])
def getChatrooms():
    if 'userID' not in session:
        error = jsonify({"problem": "Not logged in"})
        return error
    try:
        cursor, conn = quickCursor()
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (session['userID'],))
        result = cursor.fetchone()
        if not result or not result[0]:
            messageToAPI = jsonify({"signal": "ok", "chatrooms": []})
            return messageToAPI
        chatroomIDs = []
        for id in result[0].split(','):
            chatroomIDs.append(int(id))
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
        messageToAPI = jsonify({"signal": "ok", "chatrooms": chatrooms})
        return messageToAPI
    except Exception:
        print("Issue with getting user chatrooms")
        error = jsonify({"problem": "Failed to get chatrooms"})
        return error
    finally:
        quickClose(cursor,conn)

@app.route("/createChatroom", methods=["POST"])
def handleCreateChatroom():
    if 'userID' not in session:
        error =jsonify({"problem": "Not logged in"})
        return error
    dataFromAPI = request.get_json()
    name = dataFromAPI.get('name')
    if not name:
        error = jsonify({"problem": "Chatroom name is required"})
        return error
    try:
        cursor, conn = quickCursor()
        cursor.execute('INSERT INTO chatrooms (name, adminID) VALUES (?, ?)', (name, session['userID']))
        chatroomID = cursor.lastrowid
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (session['userID'],))
        result = cursor.fetchone()
        chatroomIDs = result[0].split(',') if result[0] else []
        chatroomIDs.append(str(chatroomID))
        cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', (','.join(chatroomIDs), session['userID']))
        cursor.execute(f'CREATE TABLE IF NOT EXISTS messages_{chatroomID} (id INTEGER PRIMARY KEY AUTOINCREMENT,userID INTEGER NOT NULL,message TEXT NOT NULL,timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
        conn.commit()
        messageToAPI = jsonify({"signal": "ok", "chatroom": {"id": chatroomID,"name": name,"isAdmin": True}})
        return messageToAPI
    except Exception:
        print("Issue with creating chatroom")
        conn.rollback()
        error = jsonify({"problem": "Failed to create chatroom"})
        return error
    finally:
        quickClose(cursor,conn)

@app.route("/joinChatroom", methods=["POST"])
def handleJoinChatroom():
    if 'userID' not in session:
        error = jsonify({"problem": "Not logged in"})
        return error
    dataFromAPI = request.get_json()
    chatroomID = dataFromAPI.get('chatroomID')
    if not chatroomID:
        error = jsonify({"problem": "Chatroom ID is required"})
        return error
    try:
        cursor, conn = quickCursor()
        cursor.execute('SELECT name, adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        chatroom = cursor.fetchone()
        if not chatroom:
            error = jsonify({"problem": "Chatroom not found"})
            return error
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (session['userID'],))
        result = cursor.fetchone()
        chatroomIDs = result[0].split(',') if result[0] else []
        if str(chatroomID) in chatroomIDs:
            error = jsonify({"problem": "Already in chatroom"})
            return error
        chatroomIDs.append(str(chatroomID))
        cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', (','.join(chatroomIDs), session['userID']))
        conn.commit()
        messageToAPI = jsonify({"signal": "ok", "chatroom": {"id": chatroomID,"name": chatroom[0],"isAdmin": chatroom[1] == session['userID']}})
        return messageToAPI
    except Exception:
        print("Issue with joining chatroom")
        conn.rollback()
        error =jsonify({"problem": "Failed to join chatroom"})
        return error
    finally:
        quickClose(cursor,conn)

@app.route("/leaveChatroom/<int:chatroomID>", methods=["POST"])
def handleLeaveChatroom(chatroomID):
    if 'userID' not in session:
        error =jsonify({"problem": "Not logged in"})
        return error
    try:
        cursor, conn = quickCursor()
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('SELECT adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        result = cursor.fetchone()
        if not result:
            error = jsonify({"problem": "Chatroom not found"})
            return error
        if result[0] == session['userID']:
            error = jsonify({"problem": "Admins cannot leave chatroom"})
            return error
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (session['userID'],))
        result = cursor.fetchone()
        if result and result[0]:
            chatroomIDs = result[0].split(',')
            if str(chatroomID) in chatroomIDs:
                chatroomIDs.remove(str(chatroomID))
                newChatroomIDs = ','.join(chatroomIDs) if chatroomIDs else None
                cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', (newChatroomIDs, session['userID']))
        cursor.execute('COMMIT')
        messageToAPI = jsonify({"signal": "ok"})
        return messageToAPI
    except Exception:
        print("Issue with leaving chatroom")
        cursor.execute('ROLLBACK')
        error = jsonify({"problem": "Failed to leave chatroom"})
        return error
    finally:
        quickClose(cursor,conn)

# When called to delete chatroom using curl
@app.route("/deleteChatroom/<int:chatroomID>", methods=["DELETE"])
def handleDeleteChatroom(chatroomID):
    #checks to make sure a user is able to be compared before trying
    if 'userID' not in session:
        error =jsonify({"problem": "Not logged in"})
        return error
    try:
        #connects to the database and fetches admin id from chatroom table
        cursor, conn = quickCursor()
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('SELECT adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        result = cursor.fetchone()
        #checks if there is an admin at all aka is there a chatroom
        if not result:
            error = jsonify({"problem": "Chatroom not found"})
            return error
        #checks if the user in session is an admin
        if result[0] != session['userID']:
            error = jsonify({"problem": "Not authorized"})
            return error
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
        except Exception:
            print("Issue with dropping message table")
        #finally removes the chatroom from the chatrooms database
        cursor.execute('DELETE FROM chatrooms WHERE id = ?', (chatroomID,))
        cursor.execute('COMMIT')
        messageToAPI = jsonify({"signal": "ok"})
        return messageToAPI
    except Exception:
        #undoes changes if it messes up somehow
        print("Issue with deleting chatroom")
        cursor.execute('ROLLBACK')
        error = jsonify({"problem": "Failed to delete chatroom"})
        return error
    finally:
        quickClose(cursor,conn)

@app.route("/chatroom/<int:chatroomID>/messages", methods=["GET"])
def getChatroomMessages(chatroomID):
    if 'userID' not in session:
        error = jsonify({"problem": "Not logged in"})
        return error
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        error = jsonify({"problem": "Not authorized"})
        return error
    try:
        cursor, conn = quickCursor()
        createMessageTable(chatroomID)
        cursor.execute(f'SELECT m.id, m.userID, u.username, m.message, m.timestamp FROM messages_{chatroomID} m JOIN users u ON m.userID = u.id ORDER BY m.timestamp DESC LIMIT 50')
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'userID': row[1],
                'username': row[2],
                'message': row[3],
                'timestamp': row[4]
            })
        messageToAPI = jsonify({"signal": "ok", "messages": messages[::-1]})
        return messageToAPI
    except Exception:
        print("Issue with getting messages")
        messageToAPI = jsonify({"signal": "ok", "messages": []})
        return messageToAPI
    finally:
        quickClose(cursor,conn)

@app.route("/chatroom/<int:chatroomID>/send", methods=["POST"])
def handleSendMessage(chatroomID):
    # checks if user is logged in
    if 'userID' not in session:
        error = jsonify({"problem": "Not logged in"})
        return error
    chatroom = getChatroomByID(chatroomID)
    # checks if user is in the chatroom
    if not chatroom or session['userID'] not in chatroom['users']:
        error = jsonify({"problem": "Not authorized"})
        return error
    # grabs the json data, gets the message part, and check if its empty
    dataFromAPI = request.get_json()
    message = dataFromAPI.get('message')
    if not message or not message.strip():
        error = jsonify({"problem": "Message cannot be empty"})
        return error
    try:
        # tries to open database and put message in database
        cursor, conn = quickCursor()
        createMessageTable(chatroomID)
        cursor.execute(f'INSERT INTO messages_{chatroomID} (userID, message) VALUES (?, ?)', (session['userID'], message.strip()))
        messageID = cursor.lastrowid
        # gets user from user database using the user id for message database
        cursor.execute('SELECT username FROM users WHERE id = ?', (session['userID'],))
        username = cursor.fetchone()[0]
        # pushes message and return feedback
        conn.commit()
        messageToAPI = jsonify({"signal": "ok", "message": {
            'id': messageID,
            'userID': session['userID'],
            'username': username,
            'message': message.strip(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }})
        return messageToAPI
    except Exception:
        print("Issue with sending message")
        conn.rollback()
        error = jsonify({"problem": "Failed to send message"})
        return error
    finally:
        quickClose(cursor,conn)

@app.route("/chatroom/<int:chatroomID>/stream")
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
                cursor, conn = quickCursor()
                createMessageTable(chatroomID)
                cursor.execute(f'SELECT m.id, m.userID, u.username, m.message, m.timestamp FROM messages_{chatroomID} m JOIN users u ON m.userID = u.id WHERE m.id > ? ORDER BY m.timestamp ASC', (lastID,))
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
                print("Issue in message stream")
                yield f"data: {json.dumps({'problem': str(e)})}\n\n"
            finally:
                quickClose(cursor,conn)
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream')


cursor, conn = quickCursor()
try:
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,chatroomIDs TEXT DEFAULT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS chatrooms (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,adminID INTEGER NOT NULL,FOREIGN KEY (adminID) REFERENCES users (id))')
    conn.commit()
    print("Databases created")
except Exception as e:
    print("Issue with making database")
    conn.rollback()
finally:
    quickClose(cursor,conn)
app.run(host='0.0.0.0', port=3000, debug=True)
