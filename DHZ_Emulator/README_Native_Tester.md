# 🚀 Dokumentasi: Native DHZ 8200A Treadmill Tester

Dokumen ini menjelaskan penggunaan dan cara kerja dari skrip `native_dhz_tester.py`. Skrip ini adalah hasil puncak dari *Reverse Engineering* sistem Treadmill DHZ 8200A, yang memungkinkan pengendalian mesin secara langsung (*Direct Hardware Access*) tanpa membutuhkan driver atau DLL bawaan pabrik.

---

## 🌟 Mengapa Menggunakan Skrip Native Ini?
Sebelumnya, sistem bergantung pada file `DrvtDHZ8200A.dll` yang mengharuskan penggunaan arsitektur lama (Python 32-bit / Windows jadul) dan sering mengalami *crash* memori akibat isu kompabilitas MFC (*Microsoft Foundation Classes*).

Berdasarkan temuan protokol murni dari *Reverse Engineering*, kita mengetahui bahwa mesin ini menggunakan sistem **Open Loop** (Mesin hanya menerima perintah tanpa mengirim balik verifikasi kecepatan ke PC). Oleh karena itu, skrip ini diciptakan murni menggunakan antarmuka Serial standar.

**Kelebihan Skrip Native:**
1. **100% DLL-Free**: Tidak perlu ada *file dependency* tambahan di luar Python.
2. **Support Python 64-bit**: Skrip ini berjalan sempurna di lingkungan OS modern (Windows 10/11) dengan instalasi Python standar.
3. **Debug Log Transparan**: *Developer* bisa langsung melihat *Array Byte Hexadecimal* apa yang sedang dikirim via kabel USB, sangat memudahkan pencarian *bug* pada perangkat keras.
4. **State Management Mandiri**: Kecepatan dan Kemiringan yang ditampilkan di layar dijaga secara lokal oleh variabel Python, menghindari *delay* atau proses *polling* memori yang tak perlu.

---

## 🛠️ Persyaratan Sistem (Prasyarat)
Karena tidak lagi menggunakan DLL maupun library eksternal, Anda **tidak memerlukan instalasi library apapun**. Skrip ini murni mengandalkan pustaka standar Python (`ctypes`, `os`, `sys`, `time`).

1. Install Python versi berapa saja (32-bit maupun 64-bit didukung).
2. Jalankan skrip secara langsung.

---

## 🔬 Arsitektur & Logika Kode (Cara Kerja)

Skrip ini bekerja dengan membangun dan menembakkan pesan/Array Bytes mentah (Protokol TX) ke dalam `COM Port`. Berikut adalah implementasi protokolnya di dalam skrip:

### 1. Inisialisasi Koneksi (Raw Win32 API)
Koneksi Serial dibuka secara *native* menggunakan **Win32 API** (`kernel32.CreateFileA`). Ini adalah teknik tingkat rendah (low-level) yang sama persis dengan yang digunakan oleh DLL aslinya.
- **Baudrate:** 4800
- **Parity:** None (8N1)
- **Format:** `\\\\.\\COMx` (Untuk memastikan *support* nomor port > 9 di Windows).

### 2. Format *Payload* (Data yang Dikirim)
Fungsi utama pembuatan data komunikasi ada di dalam fungsi `create_set_payload()`. Treadmill ini menerima Array kombinasi 1 Byte Header + 4 Karakter ASCII.

*   **Treadmill Start:** Mengirim *1 Byte* tunggal `[0xA1]`
*   **Treadmill Stop:** Mengirim *1 Byte* tunggal `[0xA2]`
*   **Set Kecepatan (Header `0xA3`):** 
    Kecepatan dikalikan 10, diubah ke string 4 digit (misal: 15.5 km/h $\rightarrow$ `"0155"`), kemudian tiap karakternya diubah ke wujud byte ASCII.
    *   *Payload:* `[0xA3, 0x30, 0x31, 0x35, 0x35]`
*   **Set Kemiringan / Grade (Header `0xA4`):**
    Logika matematika yang persis sama dengan kecepatan, kemiringan dikali 10, diformat 4 digit, digabung dengan Header.
    *   *Payload:* `[0xA4, 0x30, 0x31, 0x32, 0x30]` (Contoh untuk kemiringan 12.0%)

### 3. Log Debug (TX Payload Log)
Setiap kali fungsi `send_payload()` dieksekusi, skrip akan melakukan cetak layar format heksadesimal dari *byte array* (contoh: `[> TX Payload (Hex): [ A3 30 30 35 35 ] ]`). Ini adalah fitur krusial untuk melacak *bug* (memastikan algoritma perkalian x10 benar).

---

## 🎮 Cara Penggunaan (Tutorial)

1. Hubungkan kabel USB-to-Serial dari Treadmill ke PC.
2. Buka *Terminal / Command Prompt* di dalam folder `DHZ_Emulator`.
3. Jalankan perintah: 
   ```powershell
   python native_dhz_tester.py
   ```
4. Skrip akan secara otomatis **memindai** (Auto-Scan) COM Port yang tersedia. Pilih nomor port Treadmill Anda.
5. Menu interaktif akan muncul. Gunakan opsi `1` hingga `4` untuk mengetes operasional alat secara *real-time*.

---

## ⚠️ *Troubleshooting* & Penanganan Bug Khusus

Selama proses *Reverse Engineering*, kami menemukan beberapa keanehan interaksi antara sistem operasi Windows dan *driver* kabel USB-to-Serial murah (seperti CH340 atau Prolific). Skrip ini telah dirancang untuk kebal terhadap masalah-masalah berikut:

*   **Error 31: A device attached to the system is not functioning**
    *   **Penyebab:** Terjadi saat memanggil `SetCommState` untuk mengonfigurasi port. Kabel *clone* seringkali menolak konfigurasi sinyal *Flow Control* bawaan (DTR/RTS). Ini adalah alasan utama mengapa library standar seperti `PySerial` akan langsung *crash*.
    *   **Solusi di Skrip:** Menggunakan `ctypes + kernel32`, skrip akan tetap memanggil `SetCommState`, namun jika gagal (Error 31), skrip **mengabaikannya secara sengaja** dan membiarkannya lanjut. Kabel tipe ini ternyata masih bisa mengirim data TX mentah secara sempurna meskipun menolak tahap konfigurasi sistem operasi.
*   **Error 87: Invalid Parameter**
    *   **Penyebab:** Terjadi jika port dibuka dengan flag `FILE_FLAG_OVERLAPPED` (mode *Asynchronous*), tetapi instruksi pengiriman data (`WriteFile`) tidak disertai struktur `OVERLAPPED` pointer.
    *   **Solusi di Skrip:** Port dibuka murni dalam mode **Synchronous** (flag parameter bernilai `0`), sehingga fungsi `WriteFile` standar dapat langsung mengirim rentetan heksadesimal tanpa ditolak oleh Kernel Windows.
*   **Error 5: Access is Denied**
    *   Artinya *port* tersebut sedang dikunci oleh program lain. Pastikan Anda sudah menutup aplikasi *Stress ECG* yang asli, atau tutup jendela Terminal/VSCode lain yang mungkin masih menyandera (menggunakan) koneksi COM port tersebut.
*   **Error 2: File Not Found**
    *   Sistem tidak mendeteksi kabel. Kabel terlepas secara fisik dari port USB atau *driver* chip *USB-to-Serial* belum terinstal di PC.
