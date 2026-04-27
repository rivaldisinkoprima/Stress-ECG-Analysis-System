# Panduan Komprehensif: Reverse Engineering "Stress ECG Analysis System" via CLI

Dokumen ini adalah rekapitulasi lengkap dari awal persiapan *environment* hingga langkah-langkah praktis untuk mulai membedah aplikasi alat medis (ECG) berbasis Windows menggunakan Terminal.

---

## FASE 1: Setup Environment & Instalasi Tools
*(Dilakukan di PowerShell)*

### 1. Persiapan Package Manager (Scoop)
Scoop adalah *package manager* untuk Windows yang memungkinkan instalasi *tools developer* via *command line* tanpa mengubah *environment variables* sistem secara agresif.

Jalankan perintah berikut di PowerShell (tidak perlu *Run as Administrator*):

```powershell
# 1. Izinkan eksekusi script di PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 2. Install Scoop
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression

# 3. Tambahkan bucket "extras" (berisi tools tambahan seperti sysinternals)
scoop bucket add extras
```

*(Catatan: Jika mengalami error saat add extras karena file terkunci/unlink failed, jalankan `scoop bucket rm extras` lalu add kembali, atau hapus manual folder `.git` di `C:\Users\[User]\scoop\buckets\extras` dan jalankan `scoop update`).*

### 2. Instalasi "Senjata" Utama
Kita menggunakan alat *open-source* standar industri untuk membedah *binary*.

```powershell
# Install Radare2 (Disassembler) dan Sysinternals (Tools monitoring sistem Windows)
scoop install git radare2 sysinternals

# Install Python (jika belum ada)
scoop install python

# Install modul python untuk Dynamic Instrumentation dan Serial Sniffing
pip install frida-tools pyserial pyodbc
```

---

## FASE 2: Mengamankan Target (Git Versioning)
Sebelum mulai mengotak-atik file atau melakukan *patching*, kita wajib mem-*backup* status aslinya. Kita menggunakan Git agar setiap perubahan pada *binary* bisa di-*(undo)*.

```powershell
# Arahkan ke direktori target
cd "F:\val\ECG8000S\Stress ECG Analysis System"

# Inisialisasi repo terpisah khusus untuk project ini
git init
git add .
git commit -m "Initial commit: Mentahan aplikasi Stress ECG"
```

---

## FASE 3: Proses Reverse Engineering (Langkah Praktis)

### Langkah 1: Profiling Aplikasi (Menggunakan `rabin2`)
Kita harus tahu identitas asli dari aplikasi target sebelum membongkarnya.
```powershell
rabin2 -I "Stress ECG Analysis System.exe"
```
**Hasil Analisis:**
*   `arch: x86` & `bits: 32` -> Aplikasi 32-bit (Gunakan debugger x32).
*   `lang: msvc` -> Dibuat dengan C/C++ Microsoft Visual Studio.
*   `crypto: false` -> **Tidak ada proteksi/packing.** Sangat mudah dibongkar.
*   `stripped: false` -> Nama fungsi asli pengembangnya masih utuh!

### Langkah 2: Ekstraksi Informasi Teks (Menggunakan `strings`)
Banyak rahasia (password, konfigurasi, SQL) tertinggal di dalam teks mentah aplikasi.
```powershell
# Mencari perintah SQL di aplikasi utama
strings -accepteula "Stress ECG Analysis System.exe" | Select-String -Pattern "SELECT|UPDATE|INSERT"
```
**Temuan:** Aplikasi menggunakan Raw SQL Query untuk berkomunikasi dengan database Microsoft Access (`StressECG.mdb`).

### Langkah 3: Membedah Keamanan Database (`.mdb`)
Aplikasi MS Access sering kali diproteksi dengan *password*. Dari ekstraksi `strings` di atas, kita berhasil menemukan *password hardcoded*:
*   **Password Database:** `aboutface`

Kita bisa membuat script Python sederhana (`dump_mdb.py`) menggunakan library `pyodbc` untuk mengekstrak isi tabelnya:
```python
import pyodbc
db_file = r'F:\val\ECG8000S\Stress ECG Analysis System\StressECG.mdb'
conn_str = f'Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_file};PWD=aboutface;'
conn = pyodbc.connect(conn_str)
```
**Temuan:** Terdapat tabel `Cases` (berisi data pasien dan path file ECG mentah) dan tabel `Protocols` (berisi protokol *treadmill* seperti kecepatan dan kemiringan).

### Langkah 4: Melacak Konfigurasi Hardware (Registry Windows)
Karena konfigurasi *port* tidak ada di database, kita melacaknya ke Windows Registry.
```powershell
# Melacak Registry Key yang diakses oleh EquManager.exe
reg query "HKEY_CURRENT_USER\SOFTWARE\Contec Medical Systems\Contec8000TM\Settings\System" /s
```
**Temuan:** Konfigurasi COM Port disimpan dalam nilai Heksadesimal di Registry:
*   `Receiver` (Alat ECG) berjalan di **COM Port (Hex ke Decimal)**. (Contoh `04000000` = COM4)
*   `Treadmill` berjalan di **COM Port (Hex ke Decimal)**. (Contoh `0B000000` = COM11)

### Langkah 5: Analisis Komunikasi Serial di DLL (Menggunakan `r2`)
Kita tahu Contec 8000 dikendalikan oleh driver `DrvtContec8k.dll`. Kita cari bagaimana DLL ini membuka koneksi ke alat.
```powershell
# Mencari konfigurasi port serial
strings "DrvtContec8k.dll" | Select-String -Pattern "baud"
```
**Temuan:** Terdapat format string `baud=%d parity=%c data=%d stop=%d`. Ini adalah parameter fungsi `BuildCommDCBA` pada sistem Windows yang memastikan alat ECG berkomunikasi lewat **Serial Port (COM Port)**.

---

## KESIMPULAN & LANGKAH SELANJUTNYA
Aplikasi **Stress ECG Analysis System** ini memiliki beberapa celah yang memudahkan pembuatan perangkat tiruan (emulator) atau *custom gateway*:
1. **Database Terbuka:** Menggunakan MS Access dengan password *hardcoded* (`aboutface`).
2. **Konfigurasi Jelas:** Alamat COM Port dibaca langsung dari Windows Registry.
3. **Komunikasi Standar:** Menggunakan protokol Serial (RS232/USB-to-Serial) tanpa enkripsi pada *payload* pengirimannya.

**Target Selanjutnya:** Untuk membuat *gateway* mandiri seperti skrip Python Anda (`contec_08e_reader.py`), kita perlu menyadap (*sniffing*) *traffic* di COM Port yang telah diidentifikasi saat aplikasi ini terhubung ke alat ECG yang asli, agar kita bisa melihat *Handshake Sequence* dan format *byte* data ECG-nya.
