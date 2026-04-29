# 🚀 DHZ 8200A Treadmill Integration & Tester Kit

Dokumen ini merupakan hasil dari proses *Reverse Engineering* profesional terhadap aplikasi "Stress ECG Analysis System". Paket ini dirancang agar Anda (atau pengembang lain) dapat mengendalikan Treadmill **DHZ 8200A** menggunakan aplikasi pihak ketiga (Python, C#, dll) dengan memanfaatkan driver asli sebagai *bridge*.

---

## 📂 Isi Folder
1.  **`DrvtDHZ8200A.dll`**: File driver asli (hasil ekstraksi). Ini adalah "otak" yang menerjemahkan perintah aplikasi menjadi bahasa mesin (Hex) Serial/RS232.
2.  **`dhz_interactive_tester.py`**: Script Python interaktif untuk menguji fungsionalitas treadmill secara langsung via terminal.

---

## ⚠️ Prasyarat Utama (Sangat Penting)

Driver `DrvtDHZ8200A.dll` dikompilasi dalam arsitektur **32-bit (x86)**. Oleh karena itu:
*   **Wajib menggunakan Python 32-bit.** 
*   Aplikasi ini **TIDAK AKAN JALAN** jika menggunakan Python 64-bit (Sistem Anda saat ini terdeteksi menggunakan 64-bit).

### Cara Menyiapkan Lingkungan:
1.  Unduh Python 32-bit (x86) dari [python.org](https://www.python.org/downloads/windows/).
2.  Instal di direktori khusus (misal: `C:\Python32`).
3.  Jalankan script menggunakan path lengkap ke Python 32-bit tersebut:
    ```powershell
    C:\Path\Ke\Python32\python.exe dhz_interactive_tester.py
    ```

---

## 🛠️ Dokumentasi API Driver (`DrvtDHZ8200A.dll`)

Jika Anda ingin membangun aplikasi sendiri, berikut adalah fungsi-fungsi yang tersedia di dalam DLL ini:

| Fungsi | Tipe Data | Deskripsi |
| :--- | :--- | :--- |
| `DrvConnect(int port)` | `int` | Membuka koneksi Serial ke COM port yang ditentukan. |
| `DrvStart()` | `void` | Menjalankan mesin treadmill. |
| `DrvStop()` | `void` | Memberhentikan mesin treadmill secara perlahan. |
| `DrvSetSpeed(double speed)` | `double` | Mengatur kecepatan (0.0 - 20.0). |
| `DrvSetGrade(double grade)` | `double` | Mengatur kemiringan/incline (0.0 - 24.0). |
| `DrvGetSpeed()` | `double` | Membaca kecepatan aktual dari alat. |
| `DrvGetGrade()` | `double` | Membaca kemiringan aktual dari alat. |
| `DrvDisconnect()` | `void` | Memutus koneksi Serial. |

---

## 🖥️ Cara Menggunakan Tester Interaktif
1.  Buka terminal (CMD/PowerShell).
2.  Masuk ke folder ini: `cd DHZ_Emulator`.
3.  Jalankan script dengan Python 32-bit.
4.  Pilih menu **[1]** untuk menghubungkan kabel Serial ke COM Port.
5.  Pilih menu **[2]** untuk memulai pergerakan treadmill.
6.  Gunakan menu lainnya untuk mengatur kecepatan dan kemiringan secara real-time.

---

## 🔬 Catatan Hasil Analisis Statis (Radare2)
*   **Baud Rate**: Driver diatur secara default untuk berkomunikasi pada 4800 Baud.
*   **Logic**: Kecepatan di dalam kode dikalikan dengan faktor `10.0` sebelum dikonversi menjadi payload biner.
*   **Header**: Perintah awal terdeteksi menggunakan marker heksadesimal `0xA1` dan `0xA2`.

---
*Dibuat oleh Antigravity Reverse Engineering Mode.*
