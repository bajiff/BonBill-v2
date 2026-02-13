from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from functools import wraps

app = Flask(__name__)
# Kunci rahasia untuk session. Di production, gunakan Environment Variable!
app.secret_key = 'super_secret_bonbill_key_2026'

# --- KONFIGURASI DATABASE ---
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",        # Sesuaikan dengan user MySQL Anda
        password="rVzSgBU0L!Q1KZ7/", # Sesuaikan dengan password MySQL Anda

        database="db_bonbill"
    )

# --- DECORATOR KEAMANAN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            return "Akses Ditolak: Khusus Admin!", 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTING OTENTIKASI ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard_admin' if session['role'] == 'admin' else 'dashboard_user'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard_admin' if user['role'] == 'admin' else 'dashboard_user'))
        else:
            flash("Username atau password salah!")

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')", 
                           (username, hashed_password))
            conn.commit()
            flash("Registrasi berhasil! Silakan login.")
            return redirect(url_for('login'))
        except mysql.connector.Error as err:
            flash("Username sudah digunakan!")
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ROUTING USER ---
# --- ROUTING USER ---

@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard_user():
    if session['role'] == 'admin':
        return redirect(url_for('dashboard_admin'))

    if request.method == 'POST':
        try:
            table_number = int(request.form['table_number'])
            duration = int(request.form['duration'])
            start_time_str = request.form['start_time']
            
            if not (1 <= table_number <= 50) or not (1 <= duration <= 24):
                flash("Gagal: Meja (1-50) atau Durasi (1-24) tidak valid.")
                return redirect(url_for('dashboard_user'))

            new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            new_end_time = new_start_time + timedelta(hours=duration)

            conn = get_db_connection()
            cursor = conn.cursor()

            check_query = """
                SELECT id FROM bookings 
                WHERE table_number = %s 
                AND status IN ('Menunggu', 'Bermain')
                AND start_time < %s 
                AND DATE_ADD(start_time, INTERVAL duration HOUR) > %s
            """
            cursor.execute(check_query, (table_number, new_end_time, new_start_time))
            conflict = cursor.fetchone()

            if conflict:
                flash(f"Gagal: Meja {table_number} sudah dibooking pada waktu tersebut.")
            else:
                cursor.execute("""
                    INSERT INTO bookings (user_id, table_number, start_time, duration) 
                    VALUES (%s, %s, %s, %s)
                """, (session['user_id'], table_number, new_start_time, duration))
                conn.commit()
                flash("Booking berhasil dibuat! Silakan cek menu Riwayat.")
            
            cursor.close()
            conn.close()

        except Exception as e:
            flash("Terjadi kesalahan sistem atau format input salah.")

    # Jika GET, hanya render form
    return render_template('dashboard_user.html')

# USER HISTORY
@app.route('/user/history')
@login_required
def history_user():
    if session['role'] == 'admin':
        return redirect(url_for('dashboard_admin'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Read: Ambil riwayat booking milik user ini saja
    cursor.execute("SELECT * FROM bookings WHERE user_id = %s ORDER BY start_time DESC", (session['user_id'],))
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('history_user.html', bookings=bookings)
# API AVAILABLE TABLES
@app.route('/api/available_tables')
@login_required
def get_available_tables():
    start_time_str = request.args.get('start_time')
    duration_str = request.args.get('duration')

    # Jika input belum lengkap, kembalikan list kosong
    if not start_time_str or not duration_str:
        return jsonify([])

    try:
        duration = int(duration_str)
        new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        new_end_time = new_start_time + timedelta(hours=duration)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Cari meja yang SUDAH DIBOOKING pada jam tersebut
        query = """
            SELECT DISTINCT table_number FROM bookings 
            WHERE status IN ('Menunggu', 'Bermain')
            AND start_time < %s 
            AND DATE_ADD(start_time, INTERVAL duration HOUR) > %s
        """
        cursor.execute(query, (new_end_time, new_start_time))
        
        # Ekstrak nomor meja yang sibuk menjadi sebuah set Python
        booked_tables = {row['table_number'] for row in cursor.fetchall()}
        
        cursor.close()
        conn.close()

        # 2. Kalkulasi meja yang KOSONG
        # Total meja ada 50 (dari 1 sampai 50)
        all_tables = set(range(1, 51))
        # Meja kosong = Semua Meja dikurangi Meja Sibuk
        available_tables = sorted(list(all_tables - booked_tables))

        # Kembalikan sebagai format JSON agar mudah dibaca oleh JavaScript
        return jsonify(available_tables)

    except Exception as e:
        print(f"API Error: {e}")
        return jsonify([])

# --- ROUTING ADMIN ---
@app.route('/admin/dashboard')
@login_required
@admin_required
def dashboard_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Read: Admin melihat semua booking berserta nama user
    cursor.execute("""
        SELECT b.*, u.username 
        FROM bookings b 
        JOIN users u ON b.user_id = u.id 
        ORDER BY b.start_time DESC
    """)
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('dashboard_admin.html', bookings=bookings)

# ADMIN BOOKING
@app.route('/admin/add_booking', methods=['GET', 'POST'])
@login_required
@admin_required
def add_booking_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            user_id = int(request.form['user_id'])
            table_number = int(request.form['table_number'])
            duration = int(request.form['duration'])
            start_time_str = request.form['start_time']
            
            # Validasi Backend
            if not (1 <= table_number <= 50) or not (1 <= duration <= 24):
                flash("Gagal: Nomor meja (1-50) atau durasi (1-24) tidak valid.")
                return redirect(url_for('add_booking_admin'))

            new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            new_end_time = new_start_time + timedelta(hours=duration)

            # Validasi Bentrok Jadwal
            check_query = """
                SELECT id FROM bookings 
                WHERE table_number = %s 
                AND status IN ('Menunggu', 'Bermain')
                AND start_time < %s 
                AND DATE_ADD(start_time, INTERVAL duration HOUR) > %s
            """
            cursor.execute(check_query, (table_number, new_end_time, new_start_time))
            conflict = cursor.fetchone()

            if conflict:
                flash(f"Gagal: Meja {table_number} sudah dipakai pada rentang waktu tersebut.")
            else:
                cursor.execute("""
                    INSERT INTO bookings (user_id, table_number, start_time, duration, status) 
                    VALUES (%s, %s, %s, %s, 'Menunggu')
                """, (user_id, table_number, new_start_time, duration))
                conn.commit()
                flash("Sukses: Booking berhasil ditambahkan oleh Admin!")
                return redirect(url_for('dashboard_admin'))

        except ValueError:
            flash("Gagal: Format input tidak valid!")
        except Exception as e:
            flash("Terjadi kesalahan pada server.")

    # Bagian GET: Ambil daftar user untuk opsi dropdown
    cursor.execute("SELECT id, username FROM users WHERE role = 'user' ORDER BY username ASC")
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('add_booking_admin.html', users=users)

@app.route('/admin/update_status/<int:booking_id>', methods=['POST'])
@login_required
@admin_required
def update_status(booking_id):
    new_status = request.form['status']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", (new_status, booking_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard_admin'))

@app.route('/admin/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_booking(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            # Ambil data dari form admin
            user_id = int(request.form['user_id'])
            table_number = int(request.form['table_number'])
            duration = int(request.form['duration'])
            status = request.form['status']
            start_time_str = request.form['start_time']

            # Validasi Backend Tetap Berlaku untuk Admin!
            if not (1 <= table_number <= 50) or not (1 <= duration <= 24):
                flash("Error: Meja (1-50) atau Durasi (1-24) di luar batas.")
                return redirect(url_for('edit_booking', booking_id=booking_id))

            new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            new_end_time = new_start_time + timedelta(hours=duration)

            # Validasi Bentrok (KECUALI booking_id ini sendiri)
            check_query = """
                SELECT id FROM bookings 
                WHERE table_number = %s 
                AND status IN ('Menunggu', 'Bermain')
                AND id != %s 
                AND start_time < %s 
                AND DATE_ADD(start_time, INTERVAL duration HOUR) > %s
            """
            cursor.execute(check_query, (table_number, booking_id, new_end_time, new_start_time))
            conflict = cursor.fetchone()

            if conflict:
                flash(f"Gagal Update: Meja {table_number} sudah dipakai pelanggan lain pada jam tersebut!")
            else:
                # Lakukan Update
                cursor.execute("""
                    UPDATE bookings 
                    SET user_id = %s, table_number = %s, start_time = %s, duration = %s, status = %s 
                    WHERE id = %s
                """, (user_id, table_number, new_start_time, duration, status, booking_id))
                conn.commit()
                flash("Booking berhasil diupdate!")
                return redirect(url_for('dashboard_admin'))

        except ValueError:
            flash("Error: Format input tidak valid.")

    # --- Bagian GET: Tampilkan Form Edit ---
    # Ambil data booking saat ini
    cursor.execute("SELECT * FROM bookings WHERE id = %s", (booking_id,))
    booking = cursor.fetchone()
    
    # Ambil daftar semua user untuk opsi dropdown (Admin bisa ubah kepemilikan booking)
    cursor.execute("SELECT id, username FROM users WHERE role = 'user'")
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()

    if not booking:
        flash("Data booking tidak ditemukan!")
        return redirect(url_for('dashboard_admin'))

    return render_template('edit_booking_admin.html', booking=booking, users=users)
@app.route('/admin/delete/<int:booking_id>')
@login_required
@admin_required
def delete_booking(booking_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('dashboard_admin'))

if __name__ == '__main__':
    app.run(debug=True)