import sqlite3
import json

def getDBConnection():
    return sqlite3.connect('chatroom.db')

def initDB():
    conn = getDBConnection()
    cursor = conn.cursor()
    
    try:
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                chatroom_ids TEXT DEFAULT NULL
            )
        ''')
        
        # Create chatrooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chatrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                admin_id INTEGER NOT NULL,
                FOREIGN KEY (admin_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        print("Database initialized successfully")
    
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()

def createMessageTable(chatroom_id):
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS messages_{chatroom_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        conn.commit()
    except Exception as e:
        print(f"Error creating message table: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def getUserByUsername(username):
    """Get user information by username."""
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'password': user[2],
                'chatroom_ids': user[3]
            }
        return None
    finally:
        conn.close()

def getUserByID(user_id):
    """Get user information by ID."""
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'password': user[2],
                'chatroom_ids': user[3]
            }
        return None
    finally:
        conn.close()

def updateUserChatrooms(user_id, chatroom_ids):
    """Update a user's chatroom list."""
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET chatroom_ids = ? WHERE id = ?',
                      (json.dumps(chatroom_ids), user_id))
        conn.commit()
    finally:
        conn.close() 