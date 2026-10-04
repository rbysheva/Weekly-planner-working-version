import sqlite3

conn = sqlite3.connect("weekplanner.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    emoji TEXT DEFAULT '📌'
)
""")

conn.commit()
conn.close()
print("Schedule table created!")