# seed_admin.py
import mysql.connector
from werkzeug.security import generate_password_hash

def create_default_admin():
    print("Mulai proses seeding akun Admin...")
    
    try:
        # Sesuaikan dengan kredensial MySQL Anda
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="rVzSgBU0L!Q1KZ7/",
            database="db_bonbill"
        )
        cursor = conn.cursor()

        # Cek apakah username 'admin' sudah ada
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        admin_exists = cursor.fetchone()

        if admin_exists:
            print("Akun Admin sudah tersedia di database. Seeding dibatalkan.")
        else:
            # Buat akun admin baru
            # Default kredensial: Username: admin | Password: adminpassword
            hashed_pw = generate_password_hash("admininfokan")
            cursor.execute("""
                INSERT INTO users (username, password, role) 
                VALUES (%s, %s, 'admin')
            """, ('admin', hashed_pw))
            
            conn.commit()
            print("Sukses! Akun Admin berhasil dibuat.")
            print("Username : admin")
            print("Password : admininfokan")

    except mysql.connector.Error as err:
        print(f"Error Database: {err}")
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("Koneksi database ditutup.")

if __name__ == "__main__":
    create_default_admin()