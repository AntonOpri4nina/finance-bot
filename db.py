import sqlite3
from datetime import datetime
import csv
import os
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

CSV_FILE = 'stats_log.csv'
CSV_HEADER = ['user_id', 'full_name', 'username', 'action', 'source', 'timestamp']

def get_db_connection():
    """Создает и возвращает соединение с базой данных"""
    try:
        conn = sqlite3.connect('stats.db')
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        raise

def create_table():
    """Создает таблицу stats_log, если она не существует"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Создаем таблицу с правильной структурой
        c.execute('''CREATE TABLE IF NOT EXISTS stats_log
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      full_name TEXT,
                      username TEXT,
                      action TEXT,
                      source TEXT,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        
        # Создаем индексы для оптимизации запросов
        c.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON stats_log(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_action ON stats_log(action)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_source ON stats_log(source)')
        
        # Создаем таблицу для хранения времени первого взаимодействия
        c.execute('''CREATE TABLE IF NOT EXISTS user_first_interaction
                     (user_id INTEGER PRIMARY KEY,
                      first_interaction_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                      reminder_1_sent BOOLEAN DEFAULT 0,
                      reminder_3_sent BOOLEAN DEFAULT 0,
                      reminder_10_sent BOOLEAN DEFAULT 0)''')
        
        # Таблица для хранения неотвеченных событий
        c.execute('''CREATE TABLE IF NOT EXISTS pending_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event_type TEXT,
            event_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed BOOLEAN DEFAULT 0
        )''')
        
        conn.commit()
        
        # Создаём CSV с заголовком, если его нет
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADER)
            logger.info("Created new CSV file with headers")
            
        logger.info("Database table and indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        raise
    finally:
        if conn:
            conn.close()

def add_stat_row(user_id, full_name, username, action, source='direct'):
    """Добавляет строку статистики в базу данных и CSV файл"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Добавляем запись в базу данных
        c.execute('''INSERT INTO stats_log (user_id, full_name, username, action, source)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, full_name, username, action, source))
        conn.commit()
        
        # Запись в CSV
        try:
            with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([user_id, full_name, username, action, source, datetime.now().isoformat()])
        except Exception as e:
            logger.error(f"Error writing to CSV: {e}")
            # Продолжаем работу даже если не удалось записать в CSV
            
    except Exception as e:
        logger.error(f"Error adding stat row: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_source_stats():
    """Получает статистику по источникам"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT source, 
                   COUNT(*) as total_users,
                   COUNT(DISTINCT user_id) as unique_users,
                   SUM(CASE WHEN action LIKE 'get_loan_%' THEN 1 ELSE 0 END) as conversions
            FROM stats_log 
            GROUP BY source
            ORDER BY total_users DESC
        ''')
        
        return c.fetchall()
    except Exception as e:
        logger.error(f"Error getting source stats: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_stats(user_id):
    """Получает статистику по конкретному пользователю"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT action, source, timestamp
            FROM stats_log
            WHERE user_id = ?
            ORDER BY timestamp DESC
        ''', (user_id,))
        
        return c.fetchall()
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return []
    finally:
        if conn:
            conn.close()

def add_user_first_interaction(user_id):
    """Добавляет или обновляет время первого взаимодействия пользователя"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Проверяем, существует ли запись для пользователя
        c.execute('SELECT user_id FROM user_first_interaction WHERE user_id = ?', (user_id,))
        if not c.fetchone():
            # Если записи нет, создаем новую
            c.execute('INSERT INTO user_first_interaction (user_id) VALUES (?)', (user_id,))
            conn.commit()
            logger.info(f"Added first interaction time for user {user_id}")
    except Exception as e:
        logger.error(f"Error adding user first interaction: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_users_for_reminder():
    """Получает список пользователей, которым нужно отправить напоминание"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        current_time = datetime.now()
        
        # Получаем пользователей, которым нужно отправить напоминание через 1 день
        c.execute('''
            SELECT user_id, first_interaction_time 
            FROM user_first_interaction 
            WHERE reminder_1_sent = 0 
            AND datetime(first_interaction_time, '+1 day') <= datetime(?)
        ''', (current_time,))
        day_1_users = c.fetchall()
        
        # Получаем пользователей, которым нужно отправить напоминание через 3 дня
        c.execute('''
            SELECT user_id, first_interaction_time 
            FROM user_first_interaction 
            WHERE reminder_3_sent = 0 
            AND datetime(first_interaction_time, '+3 days') <= datetime(?)
        ''', (current_time,))
        day_3_users = c.fetchall()
        
        # Получаем пользователей, которым нужно отправить напоминание через 10 дней
        c.execute('''
            SELECT user_id, first_interaction_time 
            FROM user_first_interaction 
            WHERE reminder_10_sent = 0 
            AND datetime(first_interaction_time, '+10 days') <= datetime(?)
        ''', (current_time,))
        day_10_users = c.fetchall()
        
        return {
            'day_1': day_1_users,
            'day_3': day_3_users,
            'day_10': day_10_users
        }
    except Exception as e:
        logger.error(f"Error getting users for reminder: {e}")
        return {'day_1': [], 'day_3': [], 'day_10': []}
    finally:
        if conn:
            conn.close()

def mark_reminder_sent(user_id, reminder_type):
    """Отмечает, что напоминание было отправлено"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        column = f'reminder_{reminder_type}_sent'
        c.execute(f'UPDATE user_first_interaction SET {column} = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        logger.info(f"Marked {reminder_type} day reminder as sent for user {user_id}")
    except Exception as e:
        logger.error(f"Error marking reminder as sent: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# Добавить неотвеченное событие
def add_pending_event(user_id, event_type, event_data):
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''INSERT INTO pending_events (user_id, event_type, event_data) VALUES (?, ?, ?)''',
                  (user_id, event_type, event_data))
        conn.commit()
        logger.info(f"Pending event added for user {user_id}, type {event_type}")
    except Exception as e:
        logger.error(f"Error adding pending event: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

# Получить все неотвеченные события
def get_unprocessed_pending_events():
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''SELECT * FROM pending_events WHERE processed = 0 ORDER BY created_at ASC''')
        return c.fetchall()
    except Exception as e:
        logger.error(f"Error getting pending events: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Отметить событие как обработанное
def mark_pending_event_processed(event_id):
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''UPDATE pending_events SET processed = 1 WHERE id = ?''', (event_id,))
        conn.commit()
        logger.info(f"Pending event {event_id} marked as processed")
    except Exception as e:
        logger.error(f"Error marking pending event as processed: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
