import sqlite3

def getDBConnection():
    return sqlite3.connect('chatroom.db')

def createMessageTable(chatroomID):
    conn = getDBConnection()
    cursor = conn.cursor()
    try:
        cursor.execute(f'''CREATE TABLE IF NOT EXISTS messages_{chatroomID} (id INTEGER PRIMARY KEY AUTOINCREMENT,userID INTEGER NOT NULL,message TEXT NOT NULL,timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY (userID) REFERENCES users (id))''')
        conn.commit()
    except Exception as e:
        print(f"Error creating message table: {str(e)}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def getChatroomByID(chatroomID):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        chatroom = cursor.fetchone()
        if not chatroom:
            return None
        cursor.execute('SELECT id FROM users WHERE chatroomIDs LIKE ?', (f'%{chatroomID}%',))
        users = []
        for row in cursor.fetchall():
            users.append(row[0])
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