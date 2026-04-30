# 🚀 Dokumentasi Reverse Engineering: DrvtDHZ8200A.dll

Dokumen ini merupakan hasil _Reverse Engineering_ mendalam (menggunakan Radare2) terhadap _driver library_ `DrvtDHZ8200A.dll` yang mengendalikan hardware Treadmill DHZ 8200A. Seluruh analisis dilakukan pada level Assembly (x86) untuk mengungkap protokol komunikasi USB/Serial murni yang disembunyikan oleh DLL.

---

## 🛠️ Daftar Lengkap Fungsi (Exported Functions)

DLL ini mengekspos 13 fungsi global (API) yang dapat dipanggil oleh aplikasi eksternal. Berikut adalah dekompilasi dan analisis cara kerja dari masing-masing fungsi:

### 1. `DrvConnect(int port)`
*   **Hex Offset:** `0x10001490`
*   **Fungsi:** Menginisialisasi komunikasi ke treadmill.
*   **Analisis Jeroan:** 
    *   Membuat struktur memori internal (`[0x100045ec]`).
    *   Membuka _Handle_ Serial (COM Port) menggunakan _Windows API_ `CreateFileA`. Mengatur koneksi pada **4800 Baud, Parity N, Data 8, Stop 1**.
    *   Membangkitkan _Background Thread_ MFC (`AfxBeginThread`) di memori `0x10001c90` yang bertugas untuk menjaga _Heartbeat_ (menerima status dari alat secara terus-menerus).
    *   **Catatan _Legacy Bug_:** Versi bawaan DLL akan memisah format string port (`COM%d` vs `\\.\COM%d`) berdasarkan nomor port `< 10` atau `>= 10`. _Bug_ ini telah di-patch di sistem kami agar selalu menggunakan `\\.\COM%d`.

### 2. `DrvDisconnect()`
*   **Hex Offset:** `0x10001530`
*   **Fungsi:** Memutuskan koneksi komunikasi.
*   **Analisis Jeroan:** Memanggil rutin `fcn.10001c00` yang mengirimkan _event signal_ untuk membunuh _Background Thread_ pembaca data, mengosongkan antrian, dan menutup _Handle COM Port_ via `CloseHandle`.

### 3. `DrvStart()`
*   **Hex Offset:** `0x100015b0`
*   **Fungsi:** Memulai putaran motor treadmill.
*   **Analisis Payload TX:** Mengatur variabel *Speed* dan *Grade* di RAM ke angka 0, kemudian mengirimkan tepat **1 Byte Heksadesimal** ke antrian _Serial Port_:
    *   **Payload (Hex):** `[0xA1]`

### 4. `DrvStop()`
*   **Hex Offset:** `0x10001640`
*   **Fungsi:** Menghentikan motor secara perlahan (Deselerasi).
*   **Analisis Payload TX:** Mengatur variabel *Speed* dan *Grade* di RAM ke angka 0, kemudian mengirimkan tepat **1 Byte Heksadesimal**:
    *   **Payload (Hex):** `[0xA2]`

### 5. `DrvSetSpeed(double speed)`
*   **Hex Offset:** `0x10001240`
*   **Fungsi:** Mengatur kecepatan treadmill secara instan.
*   **Analisis Payload TX:** Menggunakan operasi `sprintf` untuk menggabungkan Header Hex dan nilai _double_ yang telah di-integer-kan.
    *   **Logika:** `sprintf(buffer, "\xA3%04d", speed * 10)`
    *   **Payload (Hex):** **5 Byte**. Terdiri dari Header `[0xA3]` diikuti oleh 4 Karakter ASCII.
    *   **Contoh:** Speed `15.5` $\rightarrow$ $15.5 \times 10 = 155$ $\rightarrow$ String `"0155"` $\rightarrow$ Payload: `[0xA3, 0x30, 0x31, 0x35, 0x35]`.

### 6. `DrvSetGrade(double grade)`
*   **Hex Offset:** `0x100012e0`
*   **Fungsi:** Mengatur kemiringan / Incline treadmill.
*   **Analisis Payload TX:** Konsepnya identik dengan pengatur kecepatan, menggunakan operasi matematika yang sama namun dengan Header berbeda.
    *   **Logika:** `sprintf(buffer, "\xA4%04d", grade * 10)`
    *   **Payload (Hex):** **5 Byte**. Terdiri dari Header `[0xA4]` diikuti oleh 4 Karakter ASCII.
    *   **Contoh:** Grade `5.0` $\rightarrow$ $5.0 \times 10 = 50$ $\rightarrow$ String `"0050"` $\rightarrow$ Payload: `[0xA4, 0x30, 0x30, 0x35, 0x30]`.

### 7. `DrvGetSpeed()`
*   **Hex Offset:** `0x10001380`
*   **Fungsi:** Membaca kecepatan aktual alat.
*   **Analisis Jeroan:** **[FAKE GETTER - BUKAN RX PROTOCOL]**. Ini adalah penemuan terbesar dari sesi *Reverse Engineering* ini. Fungsi ini **sama sekali tidak berkomunikasi dengan treadmill**. DLL mengimplementasikan sistem *Open Loop* (Buta). Saat Anda memanggil `DrvGetSpeed`, DLL hanya melihat ke dalam variabel memori RAM lokal (`0x100045e4`) yang sebelumnya diisi oleh pemanggilan `DrvSetSpeed`. Singkatnya: fungsi ini hanya membeo / mengembalikan angka terakhir yang Anda setel sendiri.

### 8. `DrvGetGrade()`
*   **Hex Offset:** `0x100013c0`
*   **Fungsi:** Membaca kemiringan aktual alat.
*   **Analisis Jeroan:** **[FAKE GETTER]**. Mekanismenya 100% sama dengan `DrvGetSpeed()`, mengambil dari nilai RAM lokal (`0x100045e2`) yang sebelumnya di-set oleh `DrvSetGrade`.

### 9. `DrvGetSpeedRange(double* min, double* max)`
*   **Hex Offset:** `0x100013f0`
*   **Fungsi:** Meminta referensi batas minimum dan maksimum fitur kecepatan alat.
*   **Analisis Jeroan:** Fungsi internal DLL menginjeksi nilai konstanta ke dalam alamat pointer argumen:
    *   `minSpeed` = **`0.1`** km/h
    *   `maxSpeed` = **`20.0`** km/h

### 10. `DrvGetGradeRange(double* min, double* max)`
*   **Hex Offset:** `0x10001440`
*   **Fungsi:** Meminta referensi batas minimum dan maksimum fitur kemiringan alat.
*   **Analisis Jeroan:** DLL menginjeksi nilai konstanta:
    *   `minGrade` = **`0.0`** (Datar)
    *   `maxGrade` = **`24.0`** (Tanjakan maksimal)

### 11. `DrvGetSpeedIncrement()`
*   **Hex Offset:** `0x10001700`
*   **Fungsi:** Mendapatkan langkah toleransi terkecil (perubahan) untuk memanipulasi kecepatan.
*   **Analisis Jeroan:** Me-return nilai *double* hardcoded memori `0x100032a0`.
    *   **Nilai Return:** **`0.1`**

### 12. `DrvGetGradeIncrement()`
*   **Hex Offset:** `0x10001730`
*   **Fungsi:** Mendapatkan langkah toleransi terkecil untuk memanipulasi kemiringan.
*   **Analisis Jeroan:** Me-return nilai *double* hardcoded memori `0x100032a8`.
    *   **Nilai Return:** **`1.0`**

### 13. `DrvGetSpeedUnit()`
*   **Hex Offset:** `0x100016d0`
*   **Fungsi:** Mengetahui standar satuan kecepatan yang diterapkan.
*   **Analisis Jeroan:** Mengembalikan nilai konstanta integer standar peralatan medis.
    *   **Nilai Return:** `1` (Artinya: Kilometer per Jam / km/h)

---

## 🤯 Penemuan Mengejutkan: Ketiadaan RX Protocol (Sistem *Open Loop*)
Dari hasil *tracing* arsitektur memori dengan Radare2, ditemukan fakta tak terduga: **Treadmill DHZ 8200A (atau DLL-nya) sama sekali tidak memiliki Protokol Receive (RX) / Umpan Balik**. 
Meskipun DLL membuat *Background Thread* (`0x10001c90`) yang membaca `ReadFile` dari Serial Port, hasil bacaan byte tersebut di-lempar ke *dummy function* (`fcn.10001230`) yang isinya hanya instruksi `ret` (Kosong).

Artinya, treadmill ini dioperasikan sepenuhnya secara "Buta" (*Open Loop*). PC hanya bertugas menembakkan perintah, dan treadmill menurutinya tanpa pernah memberi tahu PC apakah ia berhasil mencapai kecepatan tersebut atau tidak. 

---

## 🎯 Kesimpulan: Panduan Bypass Full-Native 

Berbekal hasil dokumentasi dan temuan arsitektur _payload_ ini, sebuah aplikasi modern (Node.js, C#, Python) kini dapat berinteraksi **tanpa perlu menggunakan file `DrvtDHZ8200A.dll` sama sekali.** 

Cukup terapkan komunikasi _Serial/RS232_ sederhana (Kirim/TX Saja) menggunakan baudrate **4800 8N1**. **Bahkan Anda tidak perlu repot-repot membuat rutin `Serial.Read()` atau `DataReceived Event` karena memang tidak ada data balasan yang divalidasi oleh sistem bawaannya.** 

Lalu tembak alat dengan Array Hex berikut:
*   Start Treadmill: `[0xA1]`
*   Stop Treadmill: `[0xA2]`
*   Set Kecepatan: `[0xA3, ASCII(digit 1), ASCII(digit 2), ASCII(digit 3), ASCII(digit 4)]`
*   Set Kemiringan: `[0xA4, ASCII(digit 1), ASCII(digit 2), ASCII(digit 3), ASCII(digit 4)]`

Contoh Praktis di Python:
```python
import serial
ser = serial.Serial('COM15', baudrate=4800, timeout=1)

# Start
ser.write(bytes([0xA1]))

# Set Speed ke 12.5 km/h (12.5 * 10 = 125 -> "0125")
# Byte: A3, '0', '1', '2', '5'
ser.write(bytes([0xA3, 0x30, 0x31, 0x32, 0x35]))
```

_Dokumentasi diturunkan berdasarkan instruksi dekompilasi memori oleh Antigravity Reverse Engineering._
