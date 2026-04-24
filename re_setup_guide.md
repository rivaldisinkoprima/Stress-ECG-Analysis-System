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
pip install frida-tools pyserial
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
*(Opsional: Anda bisa mem-push repo ini ke GitHub setelah membuat repo kosong di sana)*

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
**Temuan:** Aplikasi menggunakan Raw SQL Query (seperti `UPDATE Cases SET Deleted=1`) untuk berkomunikasi dengan database Microsoft Access (`StressECG.mdb`).

### Langkah 3: Melacak Komunikasi Alat Medis (Hardware Reversing)
Kita tahu Contec 8000 dikendalikan oleh driver `DrvtContec8k.dll`. Kita cari bagaimana DLL ini membuka koneksi ke alat.
```powershell
# Mencari konfigurasi port serial
strings "DrvtContec8k.dll" | Select-String -Pattern "baud"
```
**Temuan:** Terdapat format string `baud=%d parity=%c data=%d stop=%d`. Ini adalah parameter fungsi `BuildCommDCBA` pada sistem Windows yang memastikan alat ECG berkomunikasi lewat **Serial Port (COM Port)**.

### Langkah 4: Disassembly Tingkat Lanjut (Menggunakan `r2`)
Untuk mengetahui berapa nilai pasti dari `baud rate` (kecepatan internet alat), kita bongkar fungsi perakitnya di dalam DLL.
```powershell
# Buka DLL dengan Radare2 di terminal
r2 -A DrvtContec8k.dll

# Di dalam r2, cari referensi ke teks "baud"
> axt @@ str.*baud*

# Tampilkan kode perakit (assembly) dari fungsi tersebut
> pdf @ fcn.10001930
```
Dari perintah terakhir ini, kita bisa melihat bahwa aplikasi memanggil fungsi `CreateFileA` untuk membuka port, dan parameter `baud rate`-nya tidak di-*hardcode* melainkan diambil dari memori (kemungkinan dari database atau file *config* lain).

---

## KESIMPULAN AWAL
Aplikasi **Stress ECG Analysis System** ini tergolong **sangat rentan** dan **mudah untuk di-reverse engineer** karena:
1. Tidak ada proteksi anti-debugging atau *packing*.
2. Simbol *debugging* tidak dihapus (*not stripped*).
3. Menggunakan database Access lokal (`.mdb`) tanpa enkripsi modern.
4. Komunikasi alat dilakukan via port Serial standar yang sangat mudah disadap (*sniffing*).
