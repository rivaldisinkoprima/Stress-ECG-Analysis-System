Berikut versi Markdown (.md) yang siap kamu pakai:

# 📄 LAPORAN ANALISIS KOMUNIKASI USB DONGLE (ET99 Token)

## 1. 🎯 Tujuan
Melakukan analisis komunikasi antara aplikasi target dan USB dongle (ET99 Token) untuk memahami:
- Pola komunikasi
- Struktur data
- Mekanisme validasi (static vs dynamic)

---

## 2. 🔧 Metodologi

### Tools yang digunakan:
- USBPcap (capture USB)
- Wireshark / tshark (analisis packet)
- Command line extraction (filter payload)

### Proses:
1. Capture komunikasi saat aplikasi dijalankan
2. Ekstrak payload menggunakan:
   ```bash
   tshark -r capture.pcapng -Y "usb.data_fragment" -T fields -e frame.number -e usb.src -e usb.dst -e usb.data_fragment
Bandingkan 2 hasil capture (run berbeda)
Analisis pola dan struktur data
3. 📊 Hasil Capture (Ringkasan)
Data yang relevan (payload saja):
46000000...
46000000...

41000000ffffffff...
4100000080802155...

3c09003c...

42000000...
4. 🔁 Perbandingan Antar Run
Hasil:
Payload IDENTIK 100%
Tidak ada perubahan nilai
Tidak ada randomness
Perbedaan hanya pada:
USB path: 2.14.0 → 2.16.0

👉 Ini hanya perubahan enumerasi USB (tidak relevan)

5. 🧠 Analisis Protokol
5.1 Struktur Command
Byte Awal	Fungsi (hipotesis)
46	Inisialisasi / reset
41	Request / kirim data
3C	Trigger / proses
42	Response / hasil
5.2 Flow Komunikasi
[INIT]
46
46

[REQUEST]
41 (empty)
41 (dengan data)

[PROCESS]
3C

[RESPONSE]
42
5.3 Struktur Data

Contoh:

41 00 00 00 80 80 21 55 FF FF ...

Kemungkinan format:

[CMD][RESERVED][DATA][PADDING]
6. 🔍 Temuan Kunci
6.1 Tidak Ada Dynamic Challenge

❌ Tidak ditemukan:

nonce
random value
timestamp

✔ Semua nilai statis

6.2 Tidak Ada Enkripsi Terlihat
Tidak ada perubahan antar run
Response selalu sama

👉 indikasi:

Sistem tidak menggunakan crypto challenge-response

6.3 Sistem Bersifat Deterministik

Artinya:

Input sama → Output sama

👉 kemungkinan:

lookup table
pattern matching
6.4 Bagian Data Penting
80802155

Kemungkinan:

identifier
parameter tetap
key sederhana
7. ⚙️ Karakteristik Sistem
Aspek	Status
Randomness	❌ Tidak ada
Enkripsi	❌ Tidak terdeteksi
State machine	✔ Ada
Deterministik	✔ Ya
Kompleksitas	Low–Medium
8. 🧩 Model State Machine
START
 ↓
46 (INIT)
 ↓
41 (REQUEST)
 ↓
3C (EXECUTE)
 ↓
42 (RESPONSE)
 ↓
END
9. ⚠️ Catatan Penting

Walaupun terlihat sederhana:

Urutan command kemungkinan wajib
Timing bisa berpengaruh
Struktur HID tetap harus valid
10. 🚀 Rekomendasi untuk Reverse Engineering Software
10.1 Fokus Analisis Binary (.exe)

Cari pattern berikut di binary:

41 00 00 00
3C 09 00 3C
80802155
10.2 Cari API / Fungsi Terkait

Kemungkinan nama:

CheckDongle
ReadDongle
VerifyKey
USB HID write/read
10.3 Hook / Monitoring

Gunakan:

API Monitor
Process Monitor

Target:

fungsi komunikasi USB
HID write/read
10.4 Identifikasi Logic Validasi

Kemungkinan sederhana:

if (response == expected_pattern):
    valid = true
else:
    valid = false
11. 🧠 Kesimpulan Akhir

Sistem proteksi dongle ini menggunakan protokol statis berbasis command, tanpa mekanisme challenge-response dinamis atau kriptografi kompleks.

Implikasi:
Validasi kemungkinan berbasis pola tetap
Tidak bergantung pada perhitungan runtime
Lebih mudah dianalisis dibanding secure dongle modern
12. 📌 Status Analisis
Tahap	Status
Capture	✔ Selesai
Ekstraksi data	✔ Selesai
Analisis protokol	✔ Selesai
Reverse software	⏳ Belum
13. 🎯 Next Step
Reverse binary aplikasi
Cari mapping command di code
Identifikasi fungsi validasi
Reconstruct logic internal

---

Kalau kamu mau versi yang lebih “advance” lagi, saya bisa bantu tambahkan:
- diagram sequence (Mermaid)
- template analisis untuk IDA/Ghidra
- atau mapping byte per offset lebih detail 👍