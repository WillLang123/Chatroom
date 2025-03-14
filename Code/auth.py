from flask import session
from database import getDBConnection

def registerUser(username, password):
    """Register a new user."""
    if not username or not password:
        return {'status': 'error', 'message': 'Username and password are required'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            return {'status': 'error', 'message': 'Username already exists'}, 400
        
        # Create user with empty chatroom_ids
        cursor.execute('INSERT INTO users (username, password, chatroom_ids) VALUES (?, ?, ?)', 
                      (username, password, ''))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Set session
        session['user_id'] = user_id
        session['username'] = username
        
        return {'status': 'success', 'user': {
            'id': user_id,
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
    """Log in an existing user."""
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
        session['user_id'] = user[0]
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
    """Log out the current user."""
    try:
        session.clear()
        return {'status': 'success'}, 200
    
    except Exception as e:
        print(f"Error logging out user: {str(e)}")
        return {'status': 'error', 'message': 'Failed to log out'}, 500

def checkAuth():
    """Check if a user is authenticated."""
    try:
        if 'user_id' in session:
            return {'status': 'success', 'user': {
                'id': session['user_id'],
                'username': session['username']
            }}, 200
        return {'status': 'error', 'message': 'Not logged in'}, 401
    
    except Exception as e:
        print(f"Error checking auth: {str(e)}")
        return {'status': 'error', 'message': 'Failed to check auth'}, 500 