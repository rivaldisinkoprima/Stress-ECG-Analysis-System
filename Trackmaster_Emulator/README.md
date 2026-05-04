# 🚀 Dokumentasi Reverse Engineering: DrvtTrackMaster.dll

Dokumen ini merupakan hasil _Reverse Engineering_ mendalam (menggunakan Radare2) terhadap _driver library_ `DrvtTrackMaster.dll` yang mengendalikan hardware Treadmill TrackMaster.

---

## 🤯 Penemuan Mengejutkan: Kloning 100% Identik dengan DHZ 8200A
Dari hasil analisis _Offset, String, Export, dan Hex Dump_ pada file `DrvtTrackMaster.dll`, kami menemukan sebuah fakta yang sangat menarik: **TrackMaster secara logis menggunakan mesin protokol yang 100% SAMA PERSIS dengan Treadmill DHZ 8200A!**

Semua struktur *memory layout*, format komando (A1, A2, A3, A4), bahkan arsitektur *Open-Loop* (tanpa balasan konfirmasi kecepatan dari alat) dikompilasi dengan instruksi yang identik. Besar kemungkinan kedua produsen mesin ini menggunakan satu modul *controller board* yang sama dari Tiongkok (OEM) atau salah satu mere-branding *driver* dari yang lain.

---

## 🛠️ Spesifikasi Komunikasi Serial
Penting untuk menyetel *COM Port* pada spesifikasi berikut agar mesin merespons perintah:
*   **Baudrate:** 4800
*   **Parity:** None (N)
*   **Data Bits:** 8
*   **Stop Bits:** 1
*   **Flow Control:** None (Hardware RTS/DTR harus **dimatikan/False** untuk menghindari *Error 31* pada kabel adapter CH340/PL2303).

---

## 📦 Format Protokol Mentah (Raw Payload TX)
Skrip aplikasi Anda (*Python, Node.js, C#*) tidak perlu lagi bergantung pada DLL jadul. Cukup buka port Serial dan kirimkan Array Heksadesimal berikut:

### 1. Memulai Mesin (Start)
*   **Payload (Hex):** `[0xA1]`
*   **Keterangan:** Mengaktifkan motor treadmill.

### 2. Menghentikan Mesin (Stop)
*   **Payload (Hex):** `[0xA2]`
*   **Keterangan:** Memberhentikan motor secara deselerasi (perlahan) hingga 0.

### 3. Mengatur Kecepatan (Set Speed)
*   **Header (Hex):** `[0xA3]`
*   **Logika Data:** Nilai *double* kecepatan (km/h) dikali 10, diubah menjadi angka 4-digit bulat, kemudian dikonversi ke karakter *ASCII / Hex*.
*   **Contoh:** 12.5 km/h $\rightarrow$ 125 $\rightarrow$ String `"0125"` $\rightarrow$ ASCII Hex `[0x30, 0x31, 0x32, 0x35]`
*   **Total Payload:** `[0xA3, 0x30, 0x31, 0x32, 0x35]`

### 4. Mengatur Kemiringan (Set Grade / Incline)
*   **Header (Hex):** `[0xA4]`
*   **Logika Data:** Sama persis dengan kecepatan. Nilai *double* grade (%) dikali 10, diformat 4-digit, dan dikonversi ke karakter ASCII.
*   **Contoh:** 2.0 % $\rightarrow$ 20 $\rightarrow$ String `"0020"` $\rightarrow$ ASCII Hex `[0x30, 0x30, 0x32, 0x30]`
*   **Total Payload:** `[0xA4, 0x30, 0x30, 0x32, 0x30]`

---

## 📡 Protokol Receive (RX) - FAKE GETTER
Meskipun dalam *TrackMaster* DLL terdapat sisa-sisa instruksi pembacaan data (`ReadFile` yang merespons *header* `0xD0`, `0xD1`, `0xD2`), instruksi ini tidak mengubah hasil fungsi `DrvGetSpeed()` dan `DrvGetGrade()`. Kedua fungsi tersebut murni mem- *bypass* pembacaan mesin dengan langsung memantulkan kembali (*mirroring*) angka terakhir yang Anda setel di *Set Speed / Set Grade*.

Oleh karena itu, sistem pengendali baru (*Native*) bisa langsung menggunakan **Pendekatan Open Loop**, di mana aplikasi hanya bertindak sebagai "Pengirim/Transmitter", dan antarmuka UI di-*update* menggunakan variabel internal memori aplikasinya sendiri.

---

## 🎯 Solusi Error "A device attached to the system is not functioning (31)"
Masalah ini sangat sering terjadi saat Anda mencoba memprogram koneksi *Serial* murni menggunakan library modern seperti `PySerial` di Windows, padahal skrip `dhz_interactive_tester.py` (yang menggunakan *Windows API* kuno `CreateFileA`) berhasil terhubung.

**Apa Penyebabnya?**
`PySerial` secara bawaan mengaktifkan *Hardware Flow Control* atau memanipulasi sinyal `DTR` (Data Terminal Ready) dan `RTS` (Request to Send) sesaat sebelum membuka koneksi (*SetCommState*). Beberapa kabel adapter USB-to-Serial murah (*clone CH340 / PL2303*) tidak memiliki sirkuit pendukung untuk pin ini, sehingga sistem menolak konfigurasi dan mengeluarkan **Error 31**.

**Cara Mengatasinya di Skrip Python:**
Gunakan parameter ini saat melakukan inisialisasi PySerial:
```python
import serial

ser = serial.Serial(
    port='COM8',
    baudrate=4800,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
    xonxoff=False,   # Wajib False
    rtscts=False,    # Wajib False
    dsrdtr=False     # Wajib False
)
# Pastikan sinyal dinonaktifkan secara manual
ser.setDTR(False)
ser.setRTS(False)
```

_Dokumentasi diturunkan berdasarkan instruksi dekompilasi memori oleh Antigravity Reverse Engineering._
