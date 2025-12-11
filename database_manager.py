import sqlite3
import datetime

DB_NAME = "app_history.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            input_text TEXT,
            output_text TEXT,
            mode TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_summary_record(input_text, output_text, mode):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO chat_history (timestamp, input_text, output_text, mode)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, input_text, output_text, mode))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM chat_history ORDER BY id DESC')
    records = cursor.fetchall()
    conn.close()
    return records

def delete_record(record_id):
    """Deletes a specific record by ID."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM chat_history WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()