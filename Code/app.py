from flask import Flask, render_template, jsonify, request, session, Response
import secrets

from database import initDB
from auth import registerUser, loginUser, logoutUser, checkAuth
from chatroom import (
    getUserChatrooms,
    createChatroom,
    joinChatroom,
    deleteChatroom,
    getChatroomByID
)
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
    response, status_code = registerUser(data.get('username'), data.get('password'))
    return jsonify(response), status_code

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    response, status_code = loginUser(data.get('username'), data.get('password'))
    return jsonify(response), status_code

@app.route('/logout', methods=['POST'])
def logout():
    response, status_code = logoutUser()
    return jsonify(response), status_code

@app.route('/check_auth', methods=['GET'])
def checkAuthentication():
    response, status_code = checkAuth()
    return jsonify(response), status_code

# Chatroom routes
@app.route('/chatrooms', methods=['GET'])
def getChatrooms():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    response, status_code = getUserChatrooms(session['user_id'])
    return jsonify(response), status_code

@app.route('/create_chatroom', methods=['POST'])
def handleCreateChatroom():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    response, status_code = createChatroom(data.get('name'), session['user_id'])
    return jsonify(response), status_code

@app.route('/join_chatroom', methods=['POST'])
def handleJoinChatroom():
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    response, status_code = joinChatroom(data.get('chatroom_id'), session['user_id'])
    return jsonify(response), status_code

@app.route('/delete_chatroom/<int:chatroom_id>', methods=['DELETE'])
def handleDeleteChatroom(chatroom_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    response, status_code = deleteChatroom(chatroom_id, session['user_id'])
    return jsonify(response), status_code

# Message routes
@app.route('/chatroom/<int:chatroom_id>/messages')
def getChatroomMessages(chatroom_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    # Check if user is in the chatroom
    chatroom = getChatroomByID(chatroom_id)
    if not chatroom or session['user_id'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    
    messages = getMessages(chatroom_id)
    return jsonify({'status': 'success', 'messages': messages}), 200

@app.route('/chatroom/<int:chatroom_id>/send', methods=['POST'])
def handleSendMessage(chatroom_id):
    if 'user_id' not in session:
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401
    
    # Check if user is in the chatroom
    chatroom = getChatroomByID(chatroom_id)
    if not chatroom or session['user_id'] not in chatroom['users']:
        return jsonify({'status': 'error', 'message': 'Not authorized'}), 403
    
    data = request.get_json()
    response, status_code = sendMessage(chatroom_id, session['user_id'], data.get('message'))
    return jsonify(response), status_code

@app.route('/chatroom/<int:chatroom_id>/stream')
def streamMessages(chatroom_id):
    if 'user_id' not in session:
        return 'Not logged in', 401
    
    # Check if user is in the chatroom
    chatroom = getChatroomByID(chatroom_id)
    if not chatroom or session['user_id'] not in chatroom['users']:
        return 'Not authorized', 403
    
    return messageStream(chatroom_id)

if __name__ == '__main__':
    initDB()
    app.run(host='0.0.0.0', port=3000, debug=True)
