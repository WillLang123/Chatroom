from flask import Flask, render_template, jsonify
import sqlite3

app = Flask(__name__)

# Define the database
DATABASE = 'chat_app.db'

# Initialize the database and create necessary tables
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        chatroom_ids TEXT
                    )''')
    
    # Create chatrooms table
    cursor.execute('''CREATE TABLE IF NOT EXISTS chatrooms (
                        chatroom_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chatroom_name TEXT,
                        users TEXT,
                        admin TEXT,
                        message_table_id INTEGER
                    )''')
    
    # Commit changes and close the connection
    conn.commit()
    conn.close()

# Route to serve the HTML page
@app.route('/')
def index():
    return render_template('index.html')

# Route to initialize the database and tables (you can use this for testing)
@app.route('/init_db')
def initialize_database():
    init_db()
    return jsonify({'status': 'success', 'message': 'Database and tables created/initialized successfully'})

if __name__ == '__main__':
    # Initialize the database before running the app
    init_db()
    app.run(host='0.0.0.0', port=3000, debug=True)
