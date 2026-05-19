import sqlite3
import pandas as pd

conn = sqlite3.connect('stats.db')

# Экспорт всей статистики (таблица stats_log)
df = pd.read_sql_query("SELECT * FROM stats_log", conn)
df.to_excel('stats_export.xlsx', index=False)

# Подсчёт количества нажатий кнопок
counts = df['action'].value_counts()
print('Общее количество нажатий каждой кнопки:')
print(counts)

# Количество нажатий кнопки старт
print('Общее количество нажатий кнопки старт:', counts.get('start', 0))

conn.close()
