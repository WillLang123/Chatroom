import json
import time
from flask import Response
from database import getDBConnection

def createMessageTable(chatroom_id):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
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

def getMessages(chatroom_id, limit=50):
    """Get messages for a chatroom."""
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Ensure message table exists
        createMessageTable(chatroom_id)
        
        cursor.execute(f'''
            SELECT m.id, m.user_id, u.username, m.message, m.timestamp 
            FROM messages_{chatroom_id} m
            JOIN users u ON m.user_id = u.id
            ORDER BY m.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'message': row[3],
                'timestamp': row[4]
            })
        
        return messages[::-1]  # Reverse to get chronological order
    
    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        return []
    
    finally:
        cursor.close()
        conn.close()

def sendMessage(chatroom_id, user_id, message):
    """Send a message in a chatroom."""
    if not message or not message.strip():
        return {'status': 'error', 'message': 'Message cannot be empty'}, 400
    
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        
        # Ensure message table exists
        createMessageTable(chatroom_id)
        
        cursor.execute(f'''
            INSERT INTO messages_{chatroom_id} (user_id, message)
            VALUES (?, ?)
        ''', (user_id, message.strip()))
        
        message_id = cursor.lastrowid
        
        # Get username for the response
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        username = cursor.fetchone()[0]
        
        conn.commit()
        return {'status': 'success', 'message': {
            'id': message_id,
            'user_id': user_id,
            'username': username,
            'message': message.strip(),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }}, 200
    
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        conn.rollback()
        return {'status': 'error', 'message': 'Failed to send message'}, 500
    
    finally:
        cursor.close()
        conn.close()

def messageStream(chatroom_id):
    """Create an SSE stream for real-time message updates."""
    def generate():
        last_id = 0
        while True:
            try:
                conn = getDBConnection()
                cursor = conn.cursor()
                
                # Ensure message table exists
                createMessageTable(chatroom_id)
                
                cursor.execute(f'''
                    SELECT m.id, m.user_id, u.username, m.message, m.timestamp 
                    FROM messages_{chatroom_id} m
                    JOIN users u ON m.user_id = u.id
                    WHERE m.id > ?
                    ORDER BY m.timestamp ASC
                ''', (last_id,))
                
                messages = cursor.fetchall()
                if messages:
                    for message in messages:
                        last_id = message[0]
                        data = {
                            'id': message[0],
                            'user_id': message[1],
                            'username': message[2],
                            'message': message[3],
                            'timestamp': message[4]
                        }
                        yield f"data: {json.dumps(data)}\n\n"
            
            except Exception as e:
                print(f"Error in message stream: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            finally:
                cursor.close()
                conn.close()
            
            time.sleep(1)  # Poll every second
    
    return Response(generate(), mimetype='text/event-stream') 