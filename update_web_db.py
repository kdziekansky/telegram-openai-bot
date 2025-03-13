import sqlite3

conn = sqlite3.connect('bot_database.sqlite')
cursor = conn.cursor()

# Sprawdź, czy kolumny już istnieją
cursor.execute("PRAGMA table_info(users)")
columns = [column[1] for column in cursor.fetchall()]

# Dodaj kolumny, jeśli nie istnieją
if 'password_hash' not in columns:
    print("Dodaję kolumnę password_hash")
    cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

if 'email' not in columns:
    print("Dodaję kolumnę email")
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

conn.commit()
conn.close()

print("Aktualizacja bazy danych zakończona")