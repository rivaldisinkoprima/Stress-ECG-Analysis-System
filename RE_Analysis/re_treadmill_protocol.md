# 📄 Analisis Protokol & Arsitektur Komunikasi Treadmill pada Stress ECG System

Dokumen ini merinci bagaimana aplikasi "Stress ECG Analysis System" berinteraksi dengan berbagai merek *Treadmill* (seperti TrackMaster, DHZ8200A, Cosmos) dan bagaimana perintah-perintah heksadesimal (*hex payload*) dikonstruksi.

---

## 1. 🧩 Mengapa Aplikasi Mendukung Banyak Merek Treadmill?

Berdasarkan analisis *file system*, aplikasi utama (`Stress ECG Analysis System.exe`) **tidak memilki satupun *source code* komunikasi treadmill di dalamnya**. Sebagai gantinya, aplikasi ini menggunakan arsitektur **Plug-in berbasis DLL (Dynamic Link Library)**.

Di dalam folder instalasi, terdapat banyak *file* dengan awalan `Drvt` (Driver Treadmill), antara lain:
*   `DrvtTrackMaster.dll` (Untuk TrackMaster)
*   `DrvtDHZ8200A.dll` (Untuk DHZ 8200A)
*   `DrvtCosmos.dll` (Untuk seri Cosmos / h/p/cosmos)
*   `DrvtSch6k1.dll` (Untuk Schiller)
*   `DrvtDummy.dll` (Emulator untuk *testing* tanpa alat)

**Cara Kerjanya (Polymorphism):**
1. Saat dokter mengatur konfigurasi di aplikasi dan memilih "TrackMaster", aplikasi utama akan mengeksekusi `LoadLibrary("DrvtTrackMaster.dll")`.
2. Aplikasi utama dan semua DLL driver menyepakati sebuah **"Kontrak API Standar"**. Setiap DLL *wajib* memiliki fungsi yang di-eksport:
   *   `DrvConnect()`
   *   `DrvStart()`, `DrvStop()`
   *   `DrvSetSpeed(float speed)`
   *   `DrvSetGrade(float grade)`
3. Aplikasi utama hanya perlu memanggil `DrvSetSpeed(5.0)`. Aplikasi tidak peduli format heksadesimal apa yang dibutuhkan alat tersebut.
4. DLL `DrvtTrackMaster.dll` lah yang bertugas menerjemahkan angka `5.0` menjadi urutan *byte hex* spesifik milik TrackMaster, lalu mengirimkannya via COM Port.

---

## 2. 🔌 Alur Komunikasi Lengkap (Software <-> Treadmill)

Berikut adalah *sequence flow* komunikasi berdasarkan pembongkaran *assembly* pada `DrvtTrackMaster.dll`:

### Fase A: Inisialisasi Koneksi
1. Aplikasi utama memanggil `DrvConnect(port_number)` ke DLL.
2. DLL memanggil API Windows `CreateFileA("\\.\COMx")` untuk membuka akses Serial.
3. DLL menggunakan perintah sakti `BuildCommDCBA` dengan format *string*:
   `baud=%d parity=%c data=%d stop=%d`
   *(Misal: TrackMaster sering menggunakan Baud 4800, N, 8, 1).*
4. DLL memanggil `SetCommState()` dan `SetCommTimeouts()` untuk mengunci port.
5. DLL mengeksekusi `AfxBeginThread()` untuk membuat *thread* (proses *background*) yang secara konstan memantau port dengan `ReadFile()`.

### Fase B: Modifikasi Kecepatan / Incline (Control Flow)
Mari kita bedah fungsi `DrvSetSpeed` dari `DrvtTrackMaster.dll` (alamat fungsi `0x10001360`):
1. **Penerimaan Parameter:** Aplikasi memanggil fungsi dan mengirimkan angka kecepatan dalam format pecahan (*float/double*).
2. **Kalkulasi Floating Point:** Pada baris instruksi `fmul qword [0x100032a0]`, sistem mengalikan nilai *speed* tersebut dengan `10.0` (Hex memori `0x4024000000000000`). 
   *Contoh: Kecepatan 4.5 mph diubah menjadi `45`.*
3. **Pembulatan:** Menggunakan `fadd` dengan nilai memori `0x10003298` (kemungkinan `0.5`), sistem membulatkan angka tersebut dan mengubahnya menjadi *integer* (`_ftol`).
4. **Validasi Range:** Kode perakitan melakukan `cmp esi, 0x96` (150 dalam desimal). Ini berarti batas maksimal kecepatan yang diizinkan oleh DLL untuk alat TrackMaster versi ini adalah 15.0 mph.
5. **Konstruksi Paket (Hex Construction):** Nilai `45` tersebut akan dimasukkan ke dalam format paket berstandar pabrik.
6. **Pengiriman:** DLL memanggil fungsi internal `fcn.100011e0` yang di dalamnya mengeksekusi API `WriteFile()` dari Windows untuk menembakkan deretan *Hex* secara langsung ke alat Treadmill.

---

## 3. 🔬 Struktur Perintah Hex (Contoh TrackMaster)

Berdasarkan *pattern* perhitungan di atas dan standar industri TrackMaster, protokol komunikasi heksadesimal yang dikirim melalui `WriteFile()` umumnya terstruktur seperti ini:

Treadmill TrackMaster menggunakan protokol RS232 sederhana (tanpa enkripsi rumit).

**Format Umum Paket (Payload):**
`[Header] [Command Byte] [Data Bytes] [Checksum] [Trailer]`

Sebagai contoh (Skenario Kecepatan 4.5 mph):
1. Kecepatan dari UI (4.5) dikali 10 = `45` (Desimal).
2. `45` diubah menjadi format representasi yang diminta oleh alat. TrackMaster biasanya menggunakan representasi **ASCII Hex**. Angka `450` (karena *padding* ratusan) = ASCII karakter `4` (`0x34`), `5` (`0x35`), `0` (`0x30`).
3. **Hex Payload murni yang ditembakkan ke alat (Estimasi Standar TrackMaster TMX series):**
   `0x02` `0x53` `0x34` `0x35` `0x30` `0x03` `0xXX`
   
   *Bedah Payload:*
   *   `0x02` : STX (Start of Text / Awal Paket)
   *   `0x53` : Karakter 'S' (Command untuk mengatur Speed)
   *   `0x34 0x35 0x30` : Karakter "450" mewakili 4.50 mph.
   *   `0x03` : ETX (End of Text / Akhir Paket)
   *   `0xXX` : Checksum byte (untuk keamanan data serial)

Setiap merek *treadmill* wajib memiliki DLL tersendiri karena format *payload* di poin ke-3 ini berbeda-beda mutlak. Misalnya, alat "DHZ8200A" di `DrvtDHZ8200A.dll` mungkin tidak menggunakan ASCII, melainkan murni *binary hex* `[0xAA 0x55 0x01 0x2D 0xXX]`.

---

## 4. 🚀 Implikasi Keamanan & Rekomendasi 

Karena arsitekturnya sepenuhnya terpisah berbasis DLL (Sistem Plugin yang dimuat secara dinamis), aplikasi "Stress ECG" ini sangat **terbuka untuk disimulasikan (Emulator Injection)** atau ditunggangi.

Jika Anda ingin menjalankan aplikasi secara penuh tanpa *treadmill* asli (atau ingin membuat antarmuka pengontrol yang sama sekali baru):
1. Anda tidak perlu membongkar memori atau menyuntikkan *hook* ke aplikasi utama (`Stress ECG Analysis System.exe`).
2. Anda cukup membuat DLL sendiri menggunakan C++ (Visual Studio) dengan *export function* standar di atas (`DrvConnect`, `DrvSetSpeed`, dll).
3. Buat agar fungsi-fungsi tersebut langsung me-`return 1` (status *Success*) dan sekadar mencetak (Log) nilai kecepatannya ke file teks.
4. Ganti nama salah satu DLL bawaan (misal `DrvtTrackMaster.dll` menjadi `DrvtTrackMaster.dll.bak`).
5. Ganti nama DLL *custom* Anda menjadi `DrvtTrackMaster.dll`.
6. Saat Dokter memilih "TrackMaster", aplikasi secara otomatis akan berbicara dengan DLL buatan Anda, memungkinkan Anda memonitor atau merespon secara virtual 100% tanpa alat keras sama sekali!
