import json
from flask import session
from database import getDBConnection

def getChatroomByID(chatroom_id):
    """Get chatroom information by ID."""
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Get chatroom details
        cursor.execute('SELECT id, name, admin_id FROM chatrooms WHERE id = ?', (chatroom_id,))
        chatroom = cursor.fetchone()
        if not chatroom:
            return None
        
        # Get users in the chatroom
        cursor.execute('SELECT id FROM users WHERE chatroom_ids LIKE ?', (f'%{chatroom_id}%',))
        users = [row[0] for row in cursor.fetchall()]
        
        return {
            'id': chatroom[0],
            'name': chatroom[1],
            'admin_id': chatroom[2],
            'users': users
        }
    
    except Exception as e:
        print(f"Error getting chatroom: {str(e)}")
        return None
    
    finally:
        cursor.close()
        conn.close()

def getUserChatrooms(user_id):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Get user's chatroom IDs
        cursor.execute('SELECT chatroom_ids FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            return {'status': 'success', 'chatrooms': []}, 200
        
        chatroom_ids = [int(id) for id in result[0].split(',')]
        
        # Get chatroom details
        chatrooms = []
        for chatroom_id in chatroom_ids:
            cursor.execute('SELECT id, name, admin_id FROM chatrooms WHERE id = ?', (chatroom_id,))
            chatroom = cursor.fetchone()
            if chatroom:
                chatrooms.append({
                    'id': chatroom[0],
                    'name': chatroom[1],
                    'isAdmin': chatroom[2] == user_id
                })
        
        return {'status': 'success', 'chatrooms': chatrooms}, 200
    
    except Exception as e:
        print(f"Error getting user chatrooms: {str(e)}")
        return {'status': 'error', 'message': 'Failed to get chatrooms'}, 500
    
    finally:
        cursor.close()
        conn.close()

def createChatroom(name, user_id):
    if not name:
        return {'status': 'error', 'message': 'Chatroom name is required'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Create chatroom
        cursor.execute('INSERT INTO chatrooms (name, admin_id) VALUES (?, ?)', (name, user_id))
        chatroom_id = cursor.lastrowid
        
        # Add chatroom to user's list
        cursor.execute('SELECT chatroom_ids FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        chatroom_ids = result[0].split(',') if result[0] else []
        chatroom_ids.append(str(chatroom_id))
        
        cursor.execute('UPDATE users SET chatroom_ids = ? WHERE id = ?', 
                      (','.join(chatroom_ids), user_id))
        
        # Create messages table for the chatroom
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS messages_{chatroom_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        return {'status': 'success', 'chatroom': {
            'id': chatroom_id,
            'name': name,
            'isAdmin': True
        }}, 200
    
    except Exception as e:
        print(f"Error creating chatroom: {str(e)}")
        conn.rollback()
        return {'status': 'error', 'message': 'Failed to create chatroom'}, 500
    
    finally:
        cursor.close()
        conn.close()

def joinChatroom(chatroom_id, user_id):
    if not chatroom_id:
        return {'status': 'error', 'message': 'Chatroom ID is required'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Check if chatroom exists
        cursor.execute('SELECT name, admin_id FROM chatrooms WHERE id = ?', (chatroom_id,))
        chatroom = cursor.fetchone()
        if not chatroom:
            return {'status': 'error', 'message': 'Chatroom not found'}, 404
        
        # Check if user is already in the chatroom
        cursor.execute('SELECT chatroom_ids FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        chatroom_ids = result[0].split(',') if result[0] else []
        
        if str(chatroom_id) in chatroom_ids:
            return {'status': 'error', 'message': 'Already in chatroom'}, 400
        
        # Add chatroom to user's list
        chatroom_ids.append(str(chatroom_id))
        cursor.execute('UPDATE users SET chatroom_ids = ? WHERE id = ?', 
                      (','.join(chatroom_ids), user_id))
        
        conn.commit()
        return {'status': 'success', 'chatroom': {
            'id': chatroom_id,
            'name': chatroom[0],
            'isAdmin': chatroom[1] == user_id
        }}, 200
    
    except Exception as e:
        print(f"Error joining chatroom: {str(e)}")
        conn.rollback()
        return {'status': 'error', 'message': 'Failed to join chatroom'}, 500
    
    finally:
        cursor.close()
        conn.close()

def deleteChatroom(chatroom_id, user_id):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        cursor.execute('BEGIN TRANSACTION')
        
        # Check if chatroom exists and user is admin
        cursor.execute('SELECT admin_id FROM chatrooms WHERE id = ?', (chatroom_id,))
        result = cursor.fetchone()
        if not result:
            return {'status': 'error', 'message': 'Chatroom not found'}, 404
        if result[0] != user_id:
            return {'status': 'error', 'message': 'Not authorized'}, 403
        
        # Get all users in the chatroom
        cursor.execute('SELECT id, chatroom_ids FROM users')
        users = cursor.fetchall()
        
        # Remove chatroom from all users' lists
        for user in users:
            if user[1]:  # if user has any chatrooms
                chatroom_ids = user[1].split(',')
                if str(chatroom_id) in chatroom_ids:
                    chatroom_ids.remove(str(chatroom_id))
                    new_chatroom_ids = ','.join(chatroom_ids) if chatroom_ids else None
                    cursor.execute('UPDATE users SET chatroom_ids = ? WHERE id = ?', 
                                 (new_chatroom_ids, user[0]))
        
        # Drop messages table and delete chatroom
        cursor.execute(f'DROP TABLE IF EXISTS messages_{chatroom_id}')
        cursor.execute('DELETE FROM chatrooms WHERE id = ?', (chatroom_id,))
        
        cursor.execute('COMMIT')
        return {'status': 'success'}, 200
    
    except Exception as e:
        print(f"Error deleting chatroom: {str(e)}")
        cursor.execute('ROLLBACK')
        return {'status': 'error', 'message': 'Failed to delete chatroom'}, 500
    
    finally:
        cursor.close()
        conn.close() 