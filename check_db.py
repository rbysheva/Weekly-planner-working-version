import sqlite3

conn = sqlite3.connect("weekplanner.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM users")
print(cursor.fetchone())

cursor.execute("SELECT * FROM users")
print(cursor.fetchall())