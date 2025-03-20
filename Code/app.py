from flask import Flask, render_template, jsonify, request, session, Response
import secrets

from database import initDB
from Chatroom.Code.login import registerUser, loginUser, logoutUser, checkAuth
from chatroom import getUserChatrooms, createChatroom, joinChatroom, deleteChatroom, getChatroomByID
from messages import getMessages, sendMessage, messageStream

app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(32)  # for session management

# Route to serve the HTML page
@app.route('/')
def index():
    return render_template('index.html')

# Route to initialize the database and tables
@app.route('/init_db')
def initializeDatabase():
    initDB()
    return jsonify({'status': 'success', 'message': 'Database initialized successfully'})

# Authentication routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    response, status = registerUser(data.get('username'), data.get('password'))
    return jsonify(response), status

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    response, status = loginUser(data.get('username'), data.get('password'))
    return jsonify(response), status

@app.route('/logout', methods=['POST'])
def logout():
    response, status = logoutUser()
    return jsonify(response), status

@app.route('/check_auth', methods=['GET'])
def checkAuthentication():
    response, status = checkAuth()
    return jsonify(response), status

# Chatroom routes
@app.route('/chatrooms', methods=['GET'])
def getChatrooms():
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    response, status = getUserChatrooms(session['userID'])
    return jsonify(response), status

@app.route('/create_chatroom', methods=['POST'])
def handleCreateChatroom():
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    response, status = createChatroom(data.get('name'), session['userID'])
    return jsonify(response), status

@app.route('/join_chatroom', methods=['POST'])
def handleJoinChatroom():
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    response, status = joinChatroom(data.get('chatroomID'), session['userID'])
    return jsonify(response), status

@app.route('/delete_chatroom/<int:chatroomID>', methods=['DELETE'])
def handleDeleteChatroom(chatroomID):
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    response, status = deleteChatroom(chatroomID, session['userID'])
    return jsonify(response), status

# Message routes
@app.route('/chatroom/<int:chatroomID>/messages')
def getChatroomMessages(chatroomID):
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    # Check if user is in the chatroom
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    
    messages = getMessages(chatroomID)
    return jsonify({'status': 'success', 'messages': messages}), 200

@app.route('/chatroom/<int:chatroomID>/send', methods=['POST'])
def handleSendMessage(chatroomID):
    if 'userID' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    # Check if user is in the chatroom
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    
    data = request.get_json()
    response, status = sendMessage(chatroomID, session['userID'], data.get('message'))
    return jsonify(response), status

@app.route('/chatroom/<int:chatroomID>/stream')
def streamMessages(chatroomID):
    if 'userID' not in session:
        return 'Not logged in', 401
    
    # Check if user is in the chatroom
    chatroom = getChatroomByID(chatroomID)
    if not chatroom or session['userID'] not in chatroom['users']:
        return 'Not authorized', 403
    
    return messageStream(chatroomID)

if __name__ == '__main__':
    initDB()
    app.run(host='0.0.0.0', port=3000, debug=True)
