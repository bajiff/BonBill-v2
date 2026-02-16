from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'super_secret_bonbill_key_2026'

# --- KONFIGURASI DATABASE SQLITE ---
def get_db_connection():
    # Mengambil path absolut agar file database selalu ditemukan di server
    basedir = os.path.abspath(os.path.dirname(__file__))
    conn = sqlite3.connect(os.path.join(basedir, 'bonbill.db'))
    # Baris ini pengganti 'dictionary=True', mengubah hasil query menjadi objek yang bisa diakses seperti dict
    conn.row_factory = sqlite3.Row 
    return conn

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

# Filtering
@app.template_filter('format_datetime')
def format_datetime(value, format="%d-%m-%Y %H:%M"):
    if value is None:
        return ""
    # Jika value masih dalam bentuk string (dari SQLite), ubah ke datetime dulu
    if isinstance(value, str):
        try:
            # Sesuaikan format string yang disimpan SQLite (YYYY-MM-DD HH:MM:SS)
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return value
    return value.strftime(format)


# --- ROUTING OTENTIKASI ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard_admin' if session['role'] == 'admin' else 'dashboard_user'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
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
        try:
            conn.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'user')", 
                         (username, hashed_password))
            conn.commit()
            flash("Registrasi berhasil! Silakan login.")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Username sudah digunakan!")
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- ROUTING USER ---
@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard_user():
    if session['role'] == 'admin':
        return redirect(url_for('dashboard_admin'))

    if request.method == 'POST':
        try:
            # Ambil data dan pastikan tidak kosong
            table_number = request.form.get('table_number')
            duration = request.form.get('duration')
            start_time_str = request.form.get('start_time')

            if not all([table_number, duration, start_time_str]):
                flash("Gagal: Semua kolom harus diisi!")
                return redirect(url_for('dashboard_user'))

            table_number = int(table_number)
            duration = int(duration)
            
            # Parsing waktu dari HTML (YYYY-MM-DDTHH:MM)
            new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            
            # Validasi: Tidak boleh booking waktu lampau
            if new_start_time < datetime.now():
                flash("Gagal: Waktu mulai tidak boleh di masa lalu!")
                return redirect(url_for('dashboard_user'))

            new_end_time = new_start_time + timedelta(hours=duration)

            conn = get_db_connection()
            # Logika bentrok SQLite (Gunakan format string ISO untuk perbandingan teks)
            check_query = """
                SELECT id FROM bookings 
                WHERE table_number = ? 
                AND status IN ('Menunggu', 'Bermain')
                AND start_time < ? 
                AND datetime(start_time, '+' || duration || ' hours') > ?
            """
            conflict = conn.execute(check_query, (
                table_number, 
                new_end_time.strftime('%Y-%m-%d %H:%M:%S'), 
                new_start_time.strftime('%Y-%m-%d %H:%M:%S')
            )).fetchone()

            if conflict:
                flash(f"Gagal: Meja {table_number} sudah penuh di jam tersebut.")
            else:
                conn.execute("""
                    INSERT INTO bookings (user_id, table_number, start_time, duration, status) 
                    VALUES (?, ?, ?, ?, 'Menunggu')
                """, (session['user_id'], table_number, new_start_time.strftime('%Y-%m-%d %H:%M:%S'), duration))
                conn.commit()
                flash("Sukses: Booking berhasil dibuat!")
            conn.close()

        except ValueError as e:
            flash(f"Gagal: Format angka atau tanggal salah.")
        except Exception as e:
            print(f"Debug Error: {e}") # Muncul di terminal untuk pelacakan
            flash("Gagal: Terjadi kesalahan pada sistem.")

    return render_template('dashboard_user.html')

@app.route('/user/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def edit_booking_user(booking_id):
    conn = get_db_connection()
    # Pastikan user hanya bisa mengedit booking miliknya sendiri
    booking = conn.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, session['user_id'])).fetchone()

    if not booking:
        conn.close()
        flash("Gagal: Data tidak ditemukan atau Anda tidak punya akses.")
        return redirect(url_for('history_user'))

    if booking['status'] != 'Menunggu':
        conn.close()
        flash("Gagal: Booking yang sudah berjalan/selesai tidak bisa diubah.")
        return redirect(url_for('history_user'))

    if request.method == 'POST':
        try:
            table_number = int(request.form['table_number'])
            duration = int(request.form['duration'])
            start_time_str = request.form['start_time']
            new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            new_end_time = new_start_time + timedelta(hours=duration)

            # Cek bentrok (kecuali ID ini sendiri)
            check_query = """
                SELECT id FROM bookings WHERE table_number = ? AND id != ?
                AND status IN ('Menunggu', 'Bermain')
                AND start_time < ? AND datetime(start_time, '+' || duration || ' hours') > ?
            """
            conflict = conn.execute(check_query, (table_number, booking_id, new_end_time.strftime('%Y-%m-%d %H:%M:%S'), new_start_time.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()

            if conflict:
                flash("Gagal: Meja penuh di jam tersebut.")
            else:
                conn.execute("""
                    UPDATE bookings SET table_number = ?, start_time = ?, duration = ? 
                    WHERE id = ?
                """, (table_number, new_start_time.strftime('%Y-%m-%d %H:%M:%S'), duration, booking_id))
                conn.commit()
                flash("Sukses: Jadwal berhasil diubah.")
                return redirect(url_for('history_user'))
        except:
            flash("Gagal: Input tidak valid.")

    conn.close()
    return render_template('edit_booking_user.html', booking=booking)

@app.route('/user/history')
@login_required
def history_user():
    conn = get_db_connection()
    bookings = conn.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY start_time DESC", (session['user_id'],)).fetchall()
    conn.close()
    return render_template('history_user.html', bookings=bookings)

# --- API DROP DOWN DINAMIS ---
@app.route('/api/available_tables')
@login_required
def get_available_tables():
    start_time_str = request.args.get('start_time')
    duration_str = request.args.get('duration')

    if not start_time_str or not duration_str:
        return jsonify([])

    try:
        duration = int(duration_str)
        if not (1 <= duration <= 24): return jsonify([])

        new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        new_end_time = new_start_time + timedelta(hours=duration)

        conn = get_db_connection()
        query = """
            SELECT DISTINCT table_number FROM bookings 
            WHERE status IN ('Menunggu', 'Bermain')
            AND start_time < ? 
            AND datetime(start_time, '+' || duration || ' hours') > ?
        """
        rows = conn.execute(query, (new_end_time.strftime('%Y-%m-%d %H:%M:%S'), new_start_time.strftime('%Y-%m-%d %H:%M:%S'))).fetchall()
        booked_tables = {row['table_number'] for row in rows}
        conn.close()

        available_tables = sorted(list(set(range(1, 51)) - booked_tables))
        return jsonify(available_tables)
    except:
        return jsonify([])

# --- ROUTING ADMIN ---
@app.route('/admin/dashboard')
@login_required
@admin_required
def dashboard_admin():
    conn = get_db_connection()
    bookings = conn.execute("""
        SELECT b.*, u.username 
        FROM bookings b 
        JOIN users u ON b.user_id = u.id 
        ORDER BY b.start_time DESC
    """).fetchall()
    conn.close()
    return render_template('dashboard_admin.html', bookings=bookings)

@app.route('/admin/add_booking', methods=['GET', 'POST'])
@login_required
@admin_required
def add_booking_admin():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            user_id = request.form['user_id']
            table_number = int(request.form['table_number'])
            duration = int(request.form['duration'])
            start_time_str = request.form['start_time']
            new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            new_end_time = new_start_time + timedelta(hours=duration)

            # Query bentrok (Sama seperti user)
            check_query = """
                SELECT id FROM bookings WHERE table_number = ? 
                AND status IN ('Menunggu', 'Bermain')
                AND start_time < ? AND datetime(start_time, '+' || duration || ' hours') > ?
            """
            conflict = conn.execute(check_query, (table_number, new_end_time.strftime('%Y-%m-%d %H:%M:%S'), new_start_time.strftime('%Y-%m-%d %H:%M:%S'))).fetchone()

            if conflict:
                flash("Gagal: Meja sudah terisi.")
            else:
                conn.execute("INSERT INTO bookings (user_id, table_number, start_time, duration, status) VALUES (?, ?, ?, ?, 'Menunggu')",
                             (user_id, table_number, new_start_time.strftime('%Y-%m-%d %H:%M:%S'), duration))
                conn.commit()
                flash("Sukses: Admin berhasil menambahkan booking.")
                return redirect(url_for('dashboard_admin'))
        except:
            flash("Gagal: Periksa kembali input Anda.")

    users = conn.execute("SELECT id, username FROM users WHERE role = 'user'").fetchall()
    conn.close()
    return render_template('add_booking_admin.html', users=users)

# --- ROUTE EDIT ADMIN (PASTIKAN NAMA FUNGSINYA UNIK) ---
@app.route('/admin/edit_booking/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_booking_admin(booking_id):
    conn = get_db_connection()
    
    # Ambil data booking berdasarkan ID
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    
    if not booking:
        conn.close()
        flash("Gagal: Data booking tidak ditemukan.")
        return redirect(url_for('dashboard_admin'))

    if request.method == 'POST':
        try:
            user_id = int(request.form['user_id'])
            table_number = int(request.form['table_number'])
            duration = int(request.form['duration'])
            status = request.form['status']
            start_time_str = request.form['start_time']
            
            new_start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            new_end_time = new_start_time + timedelta(hours=duration)

            # Validasi Bentrok (Kecuali ID yang sedang diedit)
            check_query = """
                SELECT id FROM bookings 
                WHERE table_number = ? AND id != ?
                AND status IN ('Menunggu', 'Bermain')
                AND start_time < ? 
                AND datetime(start_time, '+' || duration || ' hours') > ?
            """
            conflict = conn.execute(check_query, (
                table_number, booking_id, 
                new_end_time.strftime('%Y-%m-%d %H:%M:%S'), 
                new_start_time.strftime('%Y-%m-%d %H:%M:%S')
            )).fetchone()

            if conflict:
                flash(f"Gagal: Meja {table_number} sudah terisi di jam tersebut!")
            else:
                conn.execute("""
                    UPDATE bookings 
                    SET user_id = ?, table_number = ?, start_time = ?, duration = ?, status = ? 
                    WHERE id = ?
                """, (user_id, table_number, new_start_time.strftime('%Y-%m-%d %H:%M:%S'), duration, status, booking_id))
                conn.commit()
                flash("Sukses: Data booking berhasil diperbarui!")
                conn.close()
                return redirect(url_for('dashboard_admin'))
        except Exception as e:
            flash(f"Gagal: Input tidak valid. {e}")

    # Ambil semua user untuk dropdown "Ganti Pelanggan"
    users = conn.execute("SELECT id, username FROM users WHERE role = 'user' ORDER BY username ASC").fetchall()
    conn.close()
    return render_template('edit_booking_admin.html', booking=booking, users=users)

# ADMIN DELETE
@app.route('/admin/delete/<int:booking_id>')
@login_required
@admin_required
def delete_booking(booking_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard_admin'))

if __name__ == '__main__':
    app.run(debug=True)