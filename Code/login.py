from flask import session
from database import getDBConnection

def registerUser(username, password):
    if not username or not password:
        return {'status': 'error', 'message': 'Username and password are required'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return {'status': 'error', 'message': 'Username already exists'}, 400
        
        # Create user with empty chatroomIDs
        cursor.execute('INSERT INTO users (username, password, chatroomIDs) VALUES (?, ?, ?)', 
                      (username, password, ''))
        
        userID = cursor.lastrowid
        conn.commit()
        
        # Set session
        session['userID'] = userID
        session['username'] = username
        
        return {'status': 'success', 'user': {
            'id': userID,
            'username': username
        }}, 200
    
    except Exception as e:
        print(f"Error registering user: {str(e)}")
        conn.rollback()
        return {'status': 'error', 'message': 'Failed to register user'}, 500
    
    finally:
        cursor.close()
        conn.close()

def loginUser(username, password):
    if not username or not password:
        return {'status': 'error', 'message': 'Username and password are required'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Get user
        cursor.execute('SELECT id, username, password FROM users WHERE username = ?', 
                      (username,))
        user = cursor.fetchone()
        if not user:
            return {'status': 'error', 'message': 'Invalid username or password'}, 401
        
        # Check password
        if password != user[2]:
            return {'status': 'error', 'message': 'Invalid username or password'}, 401
        
        # Set session
        session['userID'] = user[0]
        session['username'] = user[1]
        
        return {'status': 'success', 'user': {
            'id': user[0],
            'username': user[1]
        }}, 200
    
    except Exception as e:
        print(f"Error logging in user: {str(e)}")
        return {'status': 'error', 'message': 'Failed to log in'}, 500
    
    finally:
        cursor.close()
        conn.close()

def logoutUser():
    try:
        session.clear()
        return {'status': 'success'}, 200
    
    except Exception as e:
        print(f"Error logging out user: {str(e)}")
        return {'status': 'error', 'message': 'Failed to log out'}, 500

def checkAuth():
    try:
        if 'userID' in session:
            return {'status': 'success', 'user': {
                'id': session['userID'],
                'username': session['username']
            }}, 200
        return {'status': 'error', 'message': 'Not logged in'}, 401
    
    except Exception as e:
        print(f"Error checking auth: {str(e)}")
        return {'status': 'error', 'message': 'Failed to check auth'}, 500 