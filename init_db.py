import sqlite3
from werkzeug.security import generate_password_hash

# Ini akan otomatis membuat file 'db_bonbill.db' di folder Anda
conn = sqlite3.connect('db_bonbill.db')
cursor = conn.cursor()

print("Mulai membuat tabel SQLite...")

# Tabel Users
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

# Tabel Bookings
cursor.execute('''
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    table_number INTEGER NOT NULL,
    start_time DATETIME NOT NULL,
    duration INTEGER NOT NULL,
    status TEXT DEFAULT 'Menunggu',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
)
''')

# Seeding Admin
cursor.execute("SELECT * FROM users WHERE username = 'admin'")
if not cursor.fetchone():
    hashed_pw = generate_password_hash("admininfokan")
    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')", ('admin', hashed_pw))
    print("Akun Admin berhasil dibuat! (Username: admin | Pass: admininfokan)")

conn.commit()
conn.close()
print("Selesai! File bonbill.db siap digunakan.")