# 🚀 Panduan Integrasi Treadmill DHZ 8200A (Metode DLL Wrapper)

Dokumen ini ditujukan bagi **Developer / Modder** yang ingin mengendalikan Treadmill merek **DHZ 8200A** di aplikasi baru (seperti *Game Unity, Python Script, C# Windows Form, dll*), **tanpa perlu melakukan *reverse-engineering* terhadap protokol heksadesimal Serial (RS232/USB)**.

Alih-alih menyusun format *byte* Hex dari nol dan menghitung *Checksum* secara manual, kita akan menggunakan metode **"Black-Box Wrapper"**. Kita memanfaatkan file *driver* resmi bawaan aplikasi ECG yang sudah matang dan teruji, yaitu `DrvtDHZ8200A.dll`.

---

## 1. ⚙️ Arsitektur Integrasi

File `DrvtDHZ8200A.dll` bertindak sebagai "Penerjemah Independen". Ia menerima perintah sederhana berupa angka (misal: kecepatan `5.5`) dan secara otomatis mengubahnya menjadi bahasa mesin (seperti `A1 00 00...`) lalu mengirimkannya ke alat.

**Syarat Utama:**
1. Pastikan Anda menyalin file `DrvtDHZ8200A.dll` dari folder instalasi aplikasi ECG.
2. Pastikan aplikasi baru yang Anda buat berarsitektur **32-bit (x86)**, karena DLL ini dikompilasi dalam versi 32-bit (MSVC). (Jika menggunakan Python, gunakan Python versi 32-bit).

---

## 2. 🔌 Daftar API Kontrak (Fungsi yang Diekspos)

Berikut adalah daftar fungsi murni C++ (stdcall/cdecl) yang diekspos oleh DLL tersebut:

| Nama Fungsi | Parameter Masukan | Deskripsi / Fungsi |
| :--- | :--- | :--- |
| `DrvConnect(int port)` | `port` (Integer): Nomor COM Port | Membuka koneksi Serial (Mengeksekusi *CreateFileA* dan *BuildCommDCBA* di *background*). |
| `DrvDisconnect()` | (Kosong) | Memutus koneksi ke *treadmill* dan mematikan *thread*. |
| `DrvStart()` | (Kosong) | Mengirim perintah mulai (START) ke treadmill. |
| `DrvStop()` | (Kosong) | Mengirim perintah berhenti (STOP) ke treadmill. |
| `DrvSetSpeed(double speed)` | `speed` (Double/Float 8-byte) | Mengatur kecepatan. Batas maksimal (Limit) bawaan DLL adalah **20.0**. (Sistem otomatis mengali parameter dengan 10). |
| `DrvSetGrade(double grade)` | `grade` (Double/Float 8-byte) | Mengatur kemiringan (Incline). Batas maksimal bawaan DLL adalah **24.0**. |
| `DrvGetSpeed()` | (Kosong) | Mengembalikan nilai kecepatan saat ini (dari respon alat). |
| `DrvGetGrade()` | (Kosong) | Mengembalikan nilai kemiringan saat ini. |

---

## 3. 🐍 Contoh Kode Implementasi (Python)

Berikut adalah contoh langsung bagaimana seorang *modder* bisa menghubungkan aplikasi Python-nya ke DHZ 8200A dalam hitungan detik.

Buat file `dhz_controller.py` di folder yang sama dengan file `DrvtDHZ8200A.dll`:

```python
import ctypes
import time
import sys

# PENTING: Gunakan Python 32-bit!
if sys.maxsize > 2**32:
    print("WARNING: DLL ini adalah 32-bit. Harap gunakan Python versi 32-bit!")

# 1. Load Driver (DLL)
# Gunakan WinDLL jika fungsi menggunakan konvensi pemanggilan 'stdcall'
# Gunakan CDLL jika menggunakan konvensi 'cdecl' (umumnya C++ Native menggunakan cdecl)
try:
    dhz = ctypes.CDLL("./DrvtDHZ8200A.dll")
except OSError:
    print("Gagal meload DLL. Pastikan file DrvtDHZ8200A.dll ada dan Anda memakai arsitektur x86/32-bit.")
    sys.exit(1)

# Atur tipe data parameter untuk fungsi yang menerima desimal (double)
dhz.DrvSetSpeed.argtypes = [ctypes.c_double]
dhz.DrvSetGrade.argtypes = [ctypes.c_double]

def main():
    # 2. Hubungkan ke Treadmill (Misal di COM Port 4)
    com_port = 4
    print(f"[*] Menghubungkan ke COM{com_port}...")
    dhz.DrvConnect(com_port)
    time.sleep(1) # Beri jeda untuk handshake

    # 3. Jalankan Mesin
    print("[*] Mengirim perintah START...")
    dhz.DrvStart()
    time.sleep(2) # Biarkan belt treadmill mulai bergerak

    # 4. Atur Kecepatan ke 5.5 km/h
    # Modder tidak perlu tahu hex payload sama sekali! DLL yang mengurusnya.
    speed = 5.5
    print(f"[*] Mengubah kecepatan ke {speed}...")
    dhz.DrvSetSpeed(speed)
    time.sleep(3)

    # 5. Atur Kemiringan (Incline) ke level 2
    grade = 2.0
    print(f"[*] Mengubah Incline ke {grade}...")
    dhz.DrvSetGrade(grade)
    time.sleep(3)

    # 6. Berhentikan mesin
    print("[*] Mengirim perintah STOP...")
    dhz.DrvStop()
    time.sleep(1)

    # 7. Putus koneksi
    print("[*] Memutus koneksi (Disconnect)...")
    dhz.DrvDisconnect()

if __name__ == "__main__":
    main()
```

### Kesimpulan untuk Modder:
Jangan membuang waktu mencoba melakukan *sniffing* Hex ASCII/Binary dari kabel RS232, kecuali Anda membuat *hardware emulator*. Untuk membuat aplikasi *Desktop* pengendali, jadikanlah `DrvtDHZ8200A.dll` sebagai "Black-Box API" Anda! 
