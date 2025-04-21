import sqlite3
import time
from datetime import datetime
import json
import requests

DB_FILE = "apollo.db"
TIMEOUT = 60  # Increased timeout to 60 seconds
MAX_RETRIES = 5  # Maximum retries for handling locked errors

def connect_db():
    """Create a new SQLite connection with increased timeout and thread-safety."""
    return sqlite3.connect(DB_FILE, timeout=TIMEOUT, check_same_thread=False)

def execute_query(query, params=(), fetch=False, retries=MAX_RETRIES):
    """Execute SQL queries with retry logic to handle database locks."""
    attempt = 0
    while attempt < retries:
        try:
            with connect_db() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                if fetch:
                    return cursor.fetchall()
                return
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                print(f"Database locked. Retrying... (Attempt {attempt + 1}/{retries})")
                time.sleep(2 ** attempt)  # Exponential backoff
                attempt += 1
            else:
                raise
    print("Max retries reached. Could not complete the query.")

def initialize_db():
    """Creates tables, enables WAL mode, and applies connection handling optimizations."""
    with connect_db() as conn:
        cursor = conn.cursor()

        # Enable WAL mode for better concurrency
        cursor.execute('PRAGMA journal_mode=WAL;')

        # Create tables
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        conn.commit()

    print(f"Database initialized successfully with {TIMEOUT}-second timeout.")

def add_message(user_id: str, user_name: str, message: str):
    """Inserts a new message into the messages table."""
    timestamp = datetime.utcnow().isoformat()
    execute_query('''
        INSERT INTO messages (user_id, user_name, message, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, user_name, message, timestamp))

    # Define the API endpoint
    url = "http://0.0.0.0:8002/add-message"

    # Create the payload according to the MessageRequest model
    payload = {
        "user_id": user_id,  # Replace with the actual user ID
        "user_name": user_name,  # Replace with the actual user name
        "content": message  # Replace with the actual message content
    }

    # Make the POST request
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raise an error for bad responses
        data = response.json()  # Parse the JSON response

        # Print the response data
        print("Response:", data)

    except requests.exceptions.RequestException as e:
        print("Error:", e)

initialize_db()