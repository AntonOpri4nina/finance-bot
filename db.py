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
