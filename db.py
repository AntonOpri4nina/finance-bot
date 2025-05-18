import sqlite3
from datetime import datetime
import csv
import os

# Соединение с базой (файл будет создан автоматически)
conn = sqlite3.connect('stats.db')

CSV_FILE = 'stats_log.csv'
CSV_HEADER = ['user_id', 'name', 'username', 'action', 'event_time']

def create_table():
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                username TEXT,
                action TEXT,
                event_time TEXT
            )
        ''')
    # Создаём CSV с заголовком, если его нет
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)

def add_stat_row(user_id, name, username, action):
    now = datetime.now().isoformat()
    with conn:
        conn.execute(
            "INSERT INTO stats (user_id, name, username, action, event_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, username, action, now)
        )
    # Запись в CSV
    with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([user_id, name, username, action, now])
