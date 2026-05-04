# 📋 PRD — DHZ 8200A Smart Interface Box

**Product Name:** DHZ Smart Interface Box  
**Platform:** ESP32-S3 N16R8 (ESP-IDF Framework)  
**Version:** 1.0.0  
**Tanggal:** 30 April 2025  
**Status:** Planning Phase

---

## 1. 🎯 Overview & Visi Produk

### 1.1 Latar Belakang
Treadmill DHZ 8200A menggunakan protokol komunikasi serial RS232 proprietary (4800 8N1) yang selama ini hanya dapat diakses melalui driver bawaan pabrik (`DrvtDHZ8200A.dll`) yang sangat terbatas:
- Hanya berjalan di Windows 32-bit
- Memiliki ketergantungan pada library MFC (Microsoft Foundation Classes) yang usang
- Memiliki batasan nomor port COM (harus < 10)
- Rentan terhadap kegagalan driver USB-to-Serial (Error 31, Error 87)

### 1.2 Visi Produk
Membuat sebuah **"Smart Interface Box"** berbasis ESP32-S3 yang bertindak sebagai **penerjemah universal** antara dunia modern (Bluetooth/Wi-Fi/USB) dengan protokol serial proprietary treadmill DHZ 8200A — sehingga produk dapat dikontrol dari platform apapun (Windows, Android, iOS, Web) tanpa ketergantungan pada driver pabrik.

### 1.3 Proposisi Nilai Bisnis

| Sebelum (DLL) | Sesudah (Smart Box) |
|---|---|
| Hanya PC Windows 32-bit | Android, iOS, Windows, Web |
| Perlu install driver CH340 | Plug & Play |
| Rentan Error 31 / Error 87 | Zero driver issues |
| COM Port terbatas | Bluetooth / Wi-Fi |
| Tidak bisa IoT | Full IoT capable |
| Sulit dibundel sebagai produk | Produk hardware mandiri |

---

## 2. 📐 Arsitektur Sistem

```
┌─────────────────┐     BLE/Wi-Fi/USB     ┌──────────────────────────────────┐
│   HOST DEVICE   │ ◄──────────────────► │       ESP32-S3 SMART BOX         │
│  (PC / Android) │                       │                                  │
└─────────────────┘                       │  ┌────────────┐  ┌────────────┐  │
                                          │  │  BLE Stack │  │ Wi-Fi/HTTP │  │
                                          │  └─────┬──────┘  └─────┬──────┘  │
                                          │        │                │         │
                                          │  ┌─────▼────────────────▼──────┐  │
                                          │  │     Command Dispatcher      │  │
                                          │  │  (Terjemah JSON → Payload)  │  │
                                          │  └─────────────┬───────────────┘  │
                                          │                │                   │
                                          │  ┌─────────────▼───────────────┐  │
                                          │  │   UART TX Engine (4800 8N1) │  │
                                          │  │  Protokol 0xA1-0xA4 Builder │  │
                                          │  └─────────────┬───────────────┘  │
                                          └────────────────┼──────────────────┘
                                                           │ RS232 (via MAX3232)
                                                    ┌──────▼──────┐
                                                    │  DHZ 8200A  │
                                                    │  Treadmill  │
                                                    └─────────────┘
```

---

## 3. 🔩 Hardware yang Dibutuhkan

### 3.1 Komponen Utama

| No | Komponen | Spesifikasi | Fungsi | Qty |
|---|---|---|---|---|
| 1 | **MCU** | ESP32-S3 N16R8 | Otak utama sistem | 1 |
| 2 | **RS232 Converter** | MAX3232CPE / SP3232 | Level shift UART (3.3V) → RS232 (±12V) | 1 |
| 3 | **Konektor DB9** | DB9 Female | Koneksi ke port serial treadmill | 1 |
| 4 | **Regulator Daya** | AMS1117-3.3V atau MP2307 | Stabilkan tegangan supply | 1 |
| 5 | **Power Supply** | 5V 2A (DC Jack) | Daya utama box | 1 |
| 6 | **Kapasitor** | 100nF (decoupling) | Stabilkan supply ESP32 | 4 |
| 7 | **LED Indikator** | 3mm LED (Power, TX, BLE) | Status visual | 3 |
| 8 | **Resistor** | 330Ω | Current limiter untuk LED | 3 |
| 9 | **PCB / Protoboard** | Custom atau universal | Carrier board | 1 |
| 10 | **Enclosure Box** | ABS Plastik | Housing produk | 1 |

### 3.2 Spesifikasi ESP32-S3 N16R8
- **Flash:** 16MB Quad-SPI Flash
- **PSRAM:** 8MB Octal-SPI PSRAM
- **Wireless:** Wi-Fi 802.11 b/g/n + Bluetooth 5.0 LE
- **USB:** Native USB (USB OTG — bisa langsung sambung ke PC tanpa konverter eksternal)
- **UART:** 3 buah hardware UART (UART0, UART1, UART2)

### 3.3 Pemetaan Pin ESP32-S3

| Fungsi | GPIO ESP32-S3 | Keterangan |
|---|---|---|
| UART TX ke Treadmill | **GPIO17** | → Pin IN+ MAX3232 |
| UART RX dari Treadmill | **GPIO18** | ← Pin OUT- MAX3232 (opsional, Open-Loop) |
| LED Power | **GPIO1** | Via resistor 330Ω |
| LED TX Activity | **GPIO2** | Berkedip saat kirim perintah |
| LED BLE Status | **GPIO3** | Berkedip saat BLE aktif |
| USB D+ | **GPIO19** | Native USB (ESP32-S3 built-in) |
| USB D- | **GPIO20** | Native USB (ESP32-S3 built-in) |

### 3.4 Skema Koneksi MAX3232 → DB9

```
ESP32-S3              MAX3232CPE              DB9 Female (ke Treadmill)
─────────             ──────────              ─────────────────────────
GPIO17 (TX) ────────► T1IN → T1OUT ─────────► Pin 3 (RD - Receive Data)
GPIO18 (RX) ◄──────── R1OUT ← R1IN ◄───────── Pin 2 (TD - Transmit Data)
GND         ────────────────────────────────── Pin 5 (Signal Ground)
```

> **Catatan:** Walaupun sistem adalah Open-Loop (treadmill tidak mengirim data balik), tetap siapkan jalur RX untuk kemungkinan ekspansi di masa depan.

---

## 4. 🔄 Alur Komunikasi (Data Flow)

### 4.1 Alur Kirim Perintah (Command Flow)

```
[Host App]
    │
    │  JSON via BLE / HTTP / USB Serial
    │  Contoh: {"cmd": "SET_SPEED", "value": 8.5}
    ▼
[ESP32-S3: BLE/Wi-Fi Handler Task]
    │
    │  Parse JSON, validasi range nilai
    ▼
[ESP32-S3: Command Dispatcher]
    │
    │  Bangun payload sesuai protokol DHZ:
    │  SET_SPEED 8.5 → [0xA3, 0x30, 0x30, 0x38, 0x35]
    ▼
[ESP32-S3: UART TX Task]
    │
    │  uart_write_bytes(UART_NUM_1, payload, 5)
    ▼
[MAX3232: Level Shifter]
    │  3.3V UART → ±12V RS232
    ▼
[DHZ 8200A Treadmill Controller]
    │  Motor dieksekusi
```

### 4.2 Protokol Payload (Referensi RE Analysis)

| Perintah | Header | Data | Total | Contoh |
|---|---|---|---|---|
| START | `0xA1` | — | 1 byte | `[A1]` |
| STOP | `0xA2` | — | 1 byte | `[A2]` |
| SET SPEED | `0xA3` | 4 digit ASCII (nilai × 10) | 5 byte | `[A3 30 30 38 35]` untuk 8.5 km/h |
| SET GRADE | `0xA4` | 4 digit ASCII (nilai × 10) | 5 byte | `[A4 30 31 32 30]` untuk 12.0% |

### 4.3 Command JSON API (Host → ESP32)

```json
// Mulai treadmill
{"cmd": "START"}

// Hentikan treadmill
{"cmd": "STOP"}

// Set kecepatan (dalam km/h)
{"cmd": "SET_SPEED", "value": 8.5}

// Set kemiringan (dalam %)
{"cmd": "SET_GRADE", "value": 5.0}

// Baca status (state lokal ESP32)
{"cmd": "GET_STATUS"}
```

### 4.4 Response JSON (ESP32 → Host)

```json
// Response status normal
{
  "status": "OK",
  "motor": "RUNNING",
  "speed": 8.5,
  "grade": 5.0,
  "uptime_s": 3600
}

// Response error
{
  "status": "ERROR",
  "code": "OUT_OF_RANGE",
  "msg": "Speed must be between 0.0 and 20.0"
}
```

---

## 5. 🧱 Arsitektur Firmware (ESP-IDF)

### 5.1 Struktur Direktori Proyek

```
dhz-smart-box/
├── CMakeLists.txt
├── sdkconfig
├── main/
│   ├── CMakeLists.txt
│   ├── main.c                    ← Entry point, inisialisasi semua task
│   ├── dhz_protocol.c            ← Builder payload 0xA1-0xA4
│   ├── dhz_protocol.h
│   ├── uart_handler.c            ← Inisialisasi UART1 + kirim payload
│   ├── uart_handler.h
│   ├── command_dispatcher.c      ← Parse JSON → panggil protocol builder
│   ├── command_dispatcher.h
│   ├── ble_server.c              ← BLE GATT Server
│   ├── ble_server.h
│   ├── wifi_http_server.c        ← Optional: REST API via Wi-Fi
│   ├── wifi_http_server.h
│   └── led_indicator.c           ← Kontrol LED status
│       led_indicator.h
└── components/
    └── cJSON/                    ← Library parsing JSON
```

### 5.2 FreeRTOS Task Architecture

```
app_main()
 │
 ├─► [Task: ble_gatt_task]        Priority: 5 | Stack: 8KB
 │    Terima command JSON via BLE UART Service
 │    Kirim ke command_queue
 │
 ├─► [Task: http_server_task]     Priority: 4 | Stack: 8KB  (Opsional Wi-Fi)
 │    REST API endpoint /api/command
 │    Kirim ke command_queue
 │
 ├─► [Task: command_dispatch_task] Priority: 6 | Stack: 4KB
 │    Konsumsi command_queue
 │    Validasi parameter
 │    Bangun DHZ payload
 │    Kirim ke uart_tx_queue
 │
 ├─► [Task: uart_tx_task]         Priority: 7 | Stack: 4KB
 │    Konsumsi uart_tx_queue
 │    uart_write_bytes() ke UART1
 │    Kedipkan LED TX
 │
 └─► [Task: led_heartbeat_task]   Priority: 1 | Stack: 2KB
      Kedipkan LED BLE/Power sebagai tanda sistem hidup
```

### 5.3 Konfigurasi UART (ESP-IDF)

```c
// uart_handler.c
uart_config_t uart_config = {
    .baud_rate  = 4800,
    .data_bits  = UART_DATA_8_BITS,
    .parity     = UART_PARITY_DISABLE,
    .stop_bits  = UART_STOP_BITS_1,
    .flow_ctrl  = UART_HW_FLOWCTRL_DISABLE,
    .source_clk = UART_SCLK_APB,
};
uart_param_config(UART_NUM_1, &uart_config);
uart_set_pin(UART_NUM_1, GPIO_TX_TREADMILL, GPIO_RX_TREADMILL,
             UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
uart_driver_install(UART_NUM_1, 256, 256, 0, NULL, 0);
```

> **Tidak ada Error 31 di sini.** ESP-IDF berkomunikasi langsung ke register hardware UART, tidak lewat Windows driver stack.

---

## 6. 📡 Pilihan Konektivitas & Prioritas Implementasi

| Fase | Konektivitas | Kegunaan | Prioritas |
|---|---|---|---|
| **Fase 1** | USB Serial (Native USB ESP32-S3) | Pengganti langsung dari kabel CH340. Plug & Play di semua OS | **Wajib** |
| **Fase 2** | BLE (Bluetooth Low Energy) | Kontrol dari Android/iOS tanpa kabel | **Tinggi** |
| **Fase 3** | Wi-Fi REST API | Integrasi ke sistem rumah sakit / HIS (Hospital Information System) | **Sedang** |
| **Fase 4** | MQTT (via Wi-Fi) | IoT / monitoring jarak jauh | **Opsional** |

---

## 7. ✅ Acceptance Criteria (Kriteria Sukses)

### Fase 1 — USB Native
- [ ] ESP32-S3 terdeteksi di PC sebagai "DHZ Smart Interface" (bukan generic CH340)
- [ ] Perintah START, STOP, SET_SPEED, SET_GRADE dapat dikirim via USB Serial tanpa install driver tambahan
- [ ] Treadmill benar-benar merespons perintah (belt bergerak)
- [ ] Latensi perintah < 100ms

### Fase 2 — BLE
- [ ] Perangkat terdeteksi di Android sebagai "DHZ-SmartBox"
- [ ] Aplikasi Android dapat kirim perintah JSON via BLE Notify/Write
- [ ] BLE connection stabil selama minimal 1 jam sesi stress test

### Fase 3 — Keandalan & Keamanan
- [ ] Firmware bisa di-update via OTA (Over-The-Air) tanpa buka box
- [ ] Jika koneksi BLE/Wi-Fi putus, treadmill otomatis diperintahkan STOP (Safety Feature)
- [ ] Validasi range: Speed 0–20 km/h, Grade 0–24% diterapkan di firmware
- [ ] Device dapat boot kembali setelah power loss dan siap dalam < 3 detik

---

## 8. 🚧 Risiko & Mitigasi

| Risiko | Kemungkinan | Dampak | Mitigasi |
|---|---|---|---|
| Noise RS232 menyebabkan perintah korup | Sedang | Tinggi | Tambahkan checksum opsional atau ulangi perintah 2x |
| ESP32-S3 overheat di enclosure tertutup | Rendah | Sedang | Tambahkan ventilasi kecil di enclosure |
| DHZ firmware update mengubah protokol | Rendah | Tinggi | Simpan protokol di file konfigurasi (NVS/Flash), bukan hardcode |
| BLE range terbatas di ruangan banyak besi | Sedang | Sedang | Sediakan fallback USB |

---

## 9. 🗓️ Estimasi Timeline

| Milestone | Durasi | Output |
|---|---|---|
| **M1:** Setup ESP-IDF + UART TX ke Treadmill | 3 hari | Perintah START/STOP via UART berfungsi |
| **M2:** USB Native CDC + JSON Parser | 5 hari | Kontrol via USB dari PC tanpa driver |
| **M3:** BLE GATT Server | 7 hari | Kontrol dari Android/iOS |
| **M4:** Safety & Validation Logic | 3 hari | Auto-STOP, range check |
| **M5:** OTA Firmware Update | 5 hari | Update firmware via Wi-Fi |
| **M6:** PCB Design & Enclosure | 14 hari | Produk hardware siap produksi |
| **Total** | **~37 hari** | **MVP Hardware siap** |

---

## 10. 🔗 Referensi Teknis

- **Protokol Treadmill:** Hasil RE Analysis di `RE_Analysis/DHZ8200A_DLL_Documentation.md`
- **Proof of Concept:** `DHZ_Emulator/native_dhz_tester.py` — implementasi protokol yang telah tervalidasi
- **ESP-IDF UART Docs:** https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/uart.html
- **ESP-IDF BLE Docs:** https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/bluetooth/nimble/index.html
- **Chip MAX3232 Datasheet:** https://www.ti.com/product/MAX3232
