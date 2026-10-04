import sqlite3

conn = sqlite3.connect("weekplanner.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE tasks ADD COLUMN completed_date TEXT")
    print("Column completed_date added!")
except Exception as e:
    print(f"Info: {e}")

conn.commit()
conn.close()