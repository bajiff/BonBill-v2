🎱 BonBill - Billiard Table Reservation System

BonBill adalah aplikasi manajemen reservasi meja billiard berbasis web yang dirancang untuk memenuhi Tugas Akhir Mata Kuliah Basisdata Lanjut. Aplikasi ini mengintegrasikan pengolahan data relasional dengan antarmuka modern untuk memberikan pengalaman manajemen booking yang informatif dan efisien.

🌟 Fitur Utama
Aplikasi ini mencakup seluruh kriteria fitur yang diminta dalam ketentuan teknis:


Halaman Login: Validasi pengguna (Admin & User) dengan password hashing demi keamanan data.


Manajemen Data (CRUD): Fasilitas pembuatan, pembacaan, pembaruan, dan penghapusan data reservasi.


Pencegahan Overlap: Logika cerdas untuk mencegah bentrok jadwal pada meja dan waktu yang sama menggunakan fungsi Date & Time.


Dashboard Visualisasi: Penyajian data statistik penggunaan meja dalam bentuk grafik informatif.


Manajemen Laporan: Fitur pencarian dan penyajian data berdasarkan kriteria tertentu.


Sidebar Responsif: Navigasi modern menggunakan Tailwind CSS yang dioptimalkan untuk perangkat mobile dan desktop.

🛠️ Tech Stack

Bahasa Pemrograman: Python 3.12.3.

Web Framework: Flask.


Database: SQLite (untuk hosting/development) & MySQL (untuk pengumpulan tugas).


Frontend: HTML5, JavaScript (ES6+), Tailwind CSS (via CDN).

Grafik: Chart.js.

📋 Prasyarat
Sebelum menjalankan proyek, pastikan Anda telah menginstal:

Python 3.10 atau versi yang lebih baru.

Git (untuk melakukan clone).

🚀 Instalasi & Konfigurasi Lokal
Clone Repository

Bash
git clone https://github.com/BondanHehew/BonBill.git
cd BonBill
Siapkan Virtual Environment

Bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
Instalasi Library

Bash
pip install -r requirements.txt
Inisialisasi Database
Jalankan script berikut untuk membuat file database SQLite, tabel, dan akun Admin otomatis:

Bash
python init_db.py
Username Admin: admin

Password Admin: adminpassword

Jalankan Aplikasi

Bash
python app.py
Akses aplikasi di: http://127.0.0.1:5000

🗄️ Implementasi Basisdata Lanjut
Proyek ini mengimplementasikan konsep database tingkat lanjut sesuai persyaratan dokumentasi:

JOIN Query: Menghubungkan tabel users dan bookings untuk menyajikan laporan lengkap.

Trigger: Digunakan untuk mencatat log perubahan status booking secara otomatis.

Function/Procedure: Logika kalkulasi harga atau pembersihan data otomatis di sisi database.

Constraint: Penggunaan Foreign Key dengan Cascade Delete untuk menjaga integritas referensial.

📂 Struktur Proyek
Plaintext
``` text 

BonBill-v2
├── app.py              # File utama aplikasi Flask
├── init_db.py          # Script inisialisasi database SQLite
├── bonbill.db          # Database file (akan muncul setelah init)
├── requirements.txt    # Daftar library Python
├── bonbill.sql         # File dump database untuk MySQL
├── templates/          # Kumpulan file HTML (Jinja2)
│   ├── base_admin.html # Layout Master Admin
│   ├── base_user.html  # Layout Master User
│   └── ...             # Halaman fitur lainnya
└── static/             # File statis (CSS/JS tambahan)

```

📝 Pengumpulan Tugas
Sesuai instruksi tugas akhir, proyek ini menyertakan:


Source Code lengkap.


File Database (.sql) untuk kebutuhan import MySQL.


Dokumentasi Aplikasi dalam format Microsoft Word.


URL Hosting: Tersedia di PythonAnywhere (Opsional).

Author: [BondanHehew]
Mata Kuliah: Basisdata Lanjut

Langkah Selanjutnya:
Buat File: Di VS Code, buat file baru bernama README.md.

Paste Kode: Masukkan seluruh teks di atas ke dalamnya.

Commit & Push: Lakukan git add ., git commit -m "Add professional readme", lalu git push.