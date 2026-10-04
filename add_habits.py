import sqlite3

conn = sqlite3.connect("weekplanner.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    emoji TEXT DEFAULT '⭐'
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS habit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    habit_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    log_date TEXT NOT NULL,
    UNIQUE(habit_id, log_date)
)
""")

conn.commit()
conn.close()
print("Tables created!")
