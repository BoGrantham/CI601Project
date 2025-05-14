import sqlite3

with open('init.sql', 'r') as f:
    schema = f.read()

conn = sqlite3.connect('accounts.db')  # This is the actual SQLite database
cursor = conn.cursor()
cursor.executescript(schema)
conn.commit()
conn.close()

print("Database created successfully.")