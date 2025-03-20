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
                chatroomIDs TEXT DEFAULT NULL
            )
        ''')
        
        # Create chatrooms table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chatrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                adminID INTEGER NOT NULL,
                FOREIGN KEY (adminID) REFERENCES users (id)
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

def createMessageTable(chatroomID):
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS messages_{chatroomID} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userID INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (userID) REFERENCES users (id)
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
                'chatroomIDs': user[3]
            }
        return None
    finally:
        conn.close()

def getUserByID(userID):
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE id = ?', (userID,))
        user = cursor.fetchone()
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'password': user[2],
                'chatroomIDs': user[3]
            }
        return None
    finally:
        conn.close()

def updateUserChatrooms(userID, chatroomIDs):
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET chatroomIDs = ? WHERE id = ?',
                      (json.dumps(chatroomIDs), userID))
        conn.commit()
    finally:
        conn.close() 