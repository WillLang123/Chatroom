import json
import time
from flask import Response
from database import getDBConnection, createMessageTable

def getMessages(chatroomID, limit=50):
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        createMessageTable(chatroomID)
        cursor.execute(f'''
            SELECT m.id, m.userID, u.username, m.message, m.timestamp 
            FROM messages_{chatroomID} m
            JOIN users u ON m.userID = u.id
            ORDER BY m.timestamp DESC
            LIMIT ?
        ''', (limit,))
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row[0],
                'userID': row[1],
                'username': row[2],
                'message': row[3],
                'timestamp': row[4]
            })
        return messages[::-1]
    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def sendMessage(chatroomID, userID, message):
    if not message or not message.strip():
        return {'status': 'error', 'message': 'Message cannot be empty'}, 400
    try:
        conn = getDBConnection()
        cursor = conn.cursor()
        createMessageTable(chatroomID)
        cursor.execute(f'''
            INSERT INTO messages_{chatroomID} (userID, message)
            VALUES (?, ?)
        ''', (userID, message.strip()))
        messageID = cursor.lastrowid
        cursor.execute('SELECT username FROM users WHERE id = ?', (userID,))
        username = cursor.fetchone()[0]
        conn.commit()
        return {'status': 'success', 'message': {
            'id': messageID,
            'userID': userID,
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

def messageStream(chatroomID):
    def generate():
        lastID = 0
        while True:
            try:
                conn = getDBConnection()
                cursor = conn.cursor()
                createMessageTable(chatroomID)
                cursor.execute(f'''
                    SELECT m.id, m.userID, u.username, m.message, m.timestamp 
                    FROM messages_{chatroomID} m
                    JOIN users u ON m.userID = u.id
                    WHERE m.id > ?
                    ORDER BY m.timestamp ASC
                ''', (lastID,))
                messages = cursor.fetchall()
                if messages:
                    for message in messages:
                        lastID = message[0]
                        data = {
                            'id': message[0],
                            'userID': message[1],
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
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream') 