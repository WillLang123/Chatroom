import sqlite3

def quickCursor():
    connection = sqlite3.connect("chatroom.db")
    cursor = connection.cursor()
    return cursor, connection

def quickClose(cursor, connection):
    cursor.close()
    connection.close()

def createMessageTable(chatroomID):
    cursor, conn = quickCursor()
    try:
        cursor.execute(f'CREATE TABLE IF NOT EXISTS messages_{chatroomID} (id INTEGER PRIMARY KEY AUTOINCREMENT,userID INTEGER NOT NULL,message TEXT NOT NULL,timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY (userID) REFERENCES users (id))')
        conn.commit()
    except Exception as e:
        print("Error creating message table")
        conn.rollback()
    finally:
        quickClose(cursor, conn)

def getChatroomByID(chatroomID):
    try:
        cursor, conn = quickCursor()
        cursor.execute('SELECT id, name, adminID FROM chatrooms WHERE id = ?', (chatroomID,))
        chatroom = cursor.fetchone()
        if not chatroom:
            return None
        cursor.execute('SELECT id FROM users WHERE chatroomIDs LIKE ?', (f'%{chatroomID}%',))
        users = []
        for row in cursor.fetchall():
            users.append(row[0])
        return {
            "id": chatroom[0],
            "name": chatroom[1],
            "adminID": chatroom[2],
            "users": users
        }
    except Exception as e:
        print("Error getting chatroom")
        return None
    finally:
        quickClose(cursor, conn)