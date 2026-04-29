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
*   **Baud Rate**: Driver diatur secara default untuk berkomunikasi pada 4800 Baud, Parity N, Data Bits 8, Stop Bits 1.
*   **Logic**: Kecepatan di dalam kode dikalikan dengan faktor `10.0` sebelum dikonversi menjadi payload biner.
*   **Header**: Perintah awal terdeteksi menggunakan marker heksadesimal `0xA1` dan `0xA2`.

---

## 🚨 Isu MFC dan Solusi "Ultimate Bypass"

### Akar Masalah (The MFC Trap)
Saat memanggil fungsi `DrvConnect` melalui bahasa pemrograman non-C++ (seperti Python) atau non-MFC, fungsi ini selalu me-return nilai `0` (Gagal) dan meninggalkan *Windows Error Code 2* (File Not Found) atau *Error 5*.
Setelah dibedah mendalam, akar masalahnya **bukan** pada komunikasi OS maupun kabel Serial, melainkan pada pemanggilan fungsi internal **`AfxBeginThread`**. 

`DrvtDHZ8200A.dll` dirancang khusus untuk berjalan di bawah naungan aplikasi induk *Stress ECG* yang berbasis MFC (*Microsoft Foundation Classes*). Saat DLL ini dipaksa jalan di aplikasi biasa (konsol Python), fungsi `AfxBeginThread` yang bertugas membuat "Pekerja di balik layar" (*Background Thread* untuk mengirim paket Heartbeat) akan **Gagal / Return NULL** karena ia tidak menemukan instansi `CWinApp` yang valid di memori. Akibatnya, logika DLL melakukan pembatalan sepihak dan menutup paksa *Handle* komunikasi yang padahal sudah berhasil terbuka.

### Solusi Sementara (The Ultimate Bypass)
Di dalam `dhz_interactive_tester.py`, kita mengimplementasikan metode injeksi memori tingkat lanjut untuk menembus proteksi ini:
1. Memanggil `DrvConnect` untuk merangsang DLL membuat alokasi objek struktur di memori global (kita biarkan prosesnya gagal).
2. Mencari *pointer* dari *Global Object* DLL tersebut di alamat referensi internal (`Base Address + 0x45ec`).
3. Membuka COM Port dan mengonfigurasi DCB (*Timeouts, BaudRate, dsb.*) secara manual menggunakan Windows API `CreateFileA`.
4. Menginjeksi paksa *Handle Port* yang kita buka tersebut tepat ke ulu hati memori DLL di offset `[Object + 0x28]`.
5. Menghidupkan ulang *Background Thread* bawaan DLL secara paksa melewati MFC menggunakan Windows API `CreateThread` langsung menunjuk ke alamat prosedur *Heartbeat* treadmill (`Base Address + 0x1c90`).

Dengan teknik *Bypass* ini, kita bisa menggunakan fungsi bawaan seperti `DrvSetSpeed` dan `DrvStart` sepenuhnya secara fungsional melalui Python tanpa hambatan.

### 🚀 Next Steps: Membangun Aplikasi Native Permanen
Jika ke depannya Anda berencana membangun aplikasi medis pihak ketiga untuk mengatur Treadmill tanpa *hack* Python, ini adalah solusi elegan (Best Practice) yang direkomendasikan:

**Membangun Wrapper DLL C++ (MFC Extension)**
Buatlah sebuah *Project* **MFC DLL** kecil menggunakan Visual Studio (C++ x86).
1. Wrapper DLL buatan Anda akan memiliki status `AFX_MODULE_STATE` yang diinisialisasi dengan benar.
2. Wrapper ini bertugas me-load `DrvtDHZ8200A.dll` menggunakan `LoadLibrary`.
3. Wrapper mengekspos fungsi yang bersahabat (*standard C exports*) seperti `OpenTreadmill(int port)`, yang di dalamnya akan mengeksekusi `DrvConnect` dengan sempurna karena rantai *Thread MFC*-nya tidak putus.
4. Aplikasi utama (Python, C#, atau Node.js) nantinya tidak lagi memanggil `DrvtDHZ8200A.dll` langsung, melainkan memanggil "Wrapper C++" buatan Anda.

Metode *Wrapper* ini sangat dianjurkan untuk integrasi rumah sakit skala *Production* karena bebas dari risiko kebocoran memori (Memory Leak) akibat injeksi *thread* secara paksa.

---

*Dibuat oleh Antigravity Reverse Engineering Mode.*
