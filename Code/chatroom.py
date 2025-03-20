from database import getDBConnection
from flask import session

def getChatroomByID(chatroomID):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Get chatroom details
        cursor.execute('SELECT id, name, adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        chatroom = cursor.fetchone()
        if not chatroom:
            return None
        
        # Get users in the chatroom
        cursor.execute('SELECT id FROM users WHERE chatroomIDs LIKE ?', (f'%{chatroomID}%',))
        users = [row[0] for row in cursor.fetchall()]
        
        return {
            'id': chatroom[0],
            'name': chatroom[1],
            'adminID': chatroom[2],
            'users': users
        }
    
    except Exception as e:
        print(f"Error getting chatroom: {str(e)}")
        return None
    
    finally:
        cursor.close()
        conn.close()

def getUserChatrooms(userID):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Get user's chatroom IDs
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (userID,))
        result = cursor.fetchone()
        if not result or not result[0]:
            return {'status': 'success', 'chatrooms': []}, 200
        
        chatroomIDs = [int(id) for id in result[0].split(',')]
        
        # Get chatroom details
        chatrooms = []
        for chatroomID in chatroomIDs:
            cursor.execute('SELECT id, name, admin_id FROM chatrooms WHERE id = ?', (chatroomID,))
            chatroom = cursor.fetchone()
            if chatroom:
                chatrooms.append({
                    'id': chatroom[0],
                    'name': chatroom[1],
                    'isAdmin': chatroom[2] == userID
                })
        
        return {'status': 'success', 'chatrooms': chatrooms}, 200
    
    except Exception as e:
        print(f"Error getting user chatrooms: {str(e)}")
        return {'status': 'error', 'message': 'Failed to get chatrooms'}, 500
    
    finally:
        cursor.close()
        conn.close()

def createChatroom(name, userID):
    if not name:
        return {'status': 'error', 'message': 'Chatroom name is required'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Create chatroom
        cursor.execute('INSERT INTO chatrooms (name, adminID) VALUES (?, ?)', (name, userID))
        chatroomID = cursor.lastrowid
        
        # Add chatroom to user's list
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (userID,))
        result = cursor.fetchone()
        chatroomIDs = result[0].split(',') if result[0] else []
        chatroomIDs.append(str(chatroomID))
        
        cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', 
                      (','.join(chatroomIDs), userID))
        
        # Create messages table for the chatroom
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS messages_{chatroomID} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userID INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        return {'status': 'success', 'chatroom': {
            'id': chatroomID,
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

def joinChatroom(chatroomID, userID):
    if not chatroomID:
        return {'status': 'error', 'message': 'Chatroom ID is required'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Check if chatroom exists
        cursor.execute('SELECT name, adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        chatroom = cursor.fetchone()
        if not chatroom:
            return {'status': 'error', 'message': 'Chatroom not found'}, 404
        
        # Check if user is already in the chatroom
        cursor.execute('SELECT chatroomIDs FROM users WHERE id = ?', (userID,))
        result = cursor.fetchone()
        chatroomIDs = result[0].split(',') if result[0] else []
        
        if str(chatroomID) in chatroomIDs:
            return {'status': 'error', 'message': 'Already in chatroom'}, 400
        
        # Add chatroom to user's list
        chatroomIDs.append(str(chatroomID))
        cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', 
                      (','.join(chatroomIDs), userID))
        
        conn.commit()
        return {'status': 'success', 'chatroom': {
            'id': chatroomID,
            'name': chatroom[0],
            'isAdmin': chatroom[1] == userID
        }}, 200
    
    except Exception as e:
        print(f"Error joining chatroom: {str(e)}")
        conn.rollback()
        return {'status': 'error', 'message': 'Failed to join chatroom'}, 500
    
    finally:
        cursor.close()
        conn.close()

def deleteChatroom(chatroomID, userID):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        cursor.execute('BEGIN TRANSACTION')
        
        # Check if chatroom exists and user is admin
        cursor.execute('SELECT adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        result = cursor.fetchone()
        if not result:
            return {'status': 'error', 'message': 'Chatroom not found'}, 404
        if result[0] != userID:
            return {'status': 'error', 'message': 'Not authorized'}, 403
        
        # Get all users in the chatroom
        cursor.execute('SELECT id, chatroomIDs FROM users')
        users = cursor.fetchall()
        
        # Remove chatroom from all users' lists
        for user in users:
            if user[1]:  # if user has any chatrooms
                chatroomIDs = user[1].split(',')
                if str(chatroomID) in chatroomIDs:
                    chatroomIDs.remove(str(chatroomID))
                    newChatroomIDs = ','.join(chatroomIDs) if chatroomIDs else None
                    cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?', 
                                 (newChatroomIDs, user[0]))
        
        # Drop messages table and delete chatroom
        cursor.execute(f'DROP TABLE IF EXISTS messages_{chatroomID}')
        cursor.execute('DELETE FROM chatrooms WHERE id = ?', (chatroomID,))
        
        cursor.execute('COMMIT')
        return {'status': 'success'}, 200
    
    except Exception as e:
        print(f"Error deleting chatroom: {str(e)}")
        cursor.execute('ROLLBACK')
        return {'status': 'error', 'message': 'Failed to delete chatroom'}, 500
    
    finally:
        cursor.close()
        conn.close() 