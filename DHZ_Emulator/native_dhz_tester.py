import ctypes
import ctypes.wintypes
import time
import os
import sys

# ============================================================
# WINDOWS API SETUP (Tanpa PySerial - Langsung ke Kernel!)
# Ini adalah pendekatan yang sama seperti DLL aslinya bekerja.
# PySerial tidak bisa dipakai di sini karena ia memanggil
# SetCommState secara ketat dan chip CH340 clone menolaknya
# dengan Error 31. Solusinya: bypass PySerial, pakai CreateFileA.
# ============================================================
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

class COMMTIMEOUTS(ctypes.Structure):
    _fields_ = [
        ("ReadIntervalTimeout",         ctypes.wintypes.DWORD),
        ("ReadTotalTimeoutMultiplier",   ctypes.wintypes.DWORD),
        ("ReadTotalTimeoutConstant",     ctypes.wintypes.DWORD),
        ("WriteTotalTimeoutMultiplier",  ctypes.wintypes.DWORD),
        ("WriteTotalTimeoutConstant",    ctypes.wintypes.DWORD),
    ]

class DCB(ctypes.Structure):
    _fields_ = [
        ("DCBlength",  ctypes.wintypes.DWORD), ("BaudRate", ctypes.wintypes.DWORD),
        ("Flags",      ctypes.wintypes.DWORD), ("wReserved", ctypes.wintypes.WORD),
        ("XonLim",     ctypes.wintypes.WORD),  ("XoffLim",  ctypes.wintypes.WORD),
        ("ByteSize",   ctypes.c_byte),  ("Parity",   ctypes.c_byte),
        ("StopBits",   ctypes.c_byte),  ("XonChar",  ctypes.c_char),
        ("XoffChar",   ctypes.c_char),  ("ErrorChar", ctypes.c_char),
        ("EofChar",    ctypes.c_char),  ("EvtChar",  ctypes.c_char),
        ("wReserved1", ctypes.wintypes.WORD),
    ]

# State lokal (Open Loop - tidak ada RX dari mesin)
current_speed = 0.0
current_grade = 0.0
is_running = False
h_port = None
current_port = 0

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    status_port = f"{current_port}" if h_port else "TERPUTUS"
    status_motor = "RUNNING" if is_running else "STOPPED"
    
    print("=" * 60)
    print(" ========================================")
    print(" DHZ 8200A FULL-NATIVE TREADMILL CONTROLLER")
    print(" [OPEN-LOOP | 100% DLL-FREE | RAW WIN32 API]")
    print(" ========================================")
    print(f" Port   : {status_port}")
    print(f" Motor  : {status_motor}")
    print(f" Speed  : {current_speed} km/h")
    print(f" Grade  : {current_grade} %")
    print("=" * 60)

def scan_com_ports():
    """Scan COM Port yang benar-benar aktif menggunakan pyserial utility (scan-only)."""
    import serial.tools.list_ports
    print("[*] Memindai COM Port yang aktif...")
    ports = serial.tools.list_ports.comports()
    # Mengembalikan list tuple (device, description)
    return [(p.device, p.description) for p in ports]

def open_port(port_name):
    """
    Membuka dan mengkonfigurasi COM Port via Win32 API langsung.
    port_name bisa berupa 'COM8' atau '\\\\.\\COM8'
    """
    if not port_name.startswith("\\\\.\\"):
        port_path = f"\\\\.\\{port_name}".encode('ascii')
    else:
        port_path = port_name.encode('ascii')
        
    INVALID_HANDLE = ctypes.wintypes.HANDLE(-1).value

    print(f"\n--- [DEBUG] Membuka {port_name} ---")

    # Step 1: CreateFileA
    h = kernel32.CreateFileA(
        port_path,
        0xC0000000,   # GENERIC_READ | GENERIC_WRITE
        0,            # No sharing
        None,
        3,            # OPEN_EXISTING
        0,            # Synchronous I/O (bukan Overlapped) - wajib untuk WriteFile biasa
        None
    )
    if h == INVALID_HANDLE or h == 0:
        err = ctypes.get_last_error()
        keterangan = {
            5:  "Access Denied - dikunci aplikasi lain (tutup aplikasi lain dulu!)",
            2:  "File Not Found - kabel tidak dicolok atau driver belum terinstal",
            31: "A device attached is not functioning - hardware error",
        }.get(err, f"Unknown Win32 Error")
        print(f"[-] CreateFileA GAGAL! Error {err}: {keterangan}")
        return None
    print(f"[+] CreateFileA OK  -> Handle = {h}")

    # Step 2: SetCommTimeouts
    timeouts = COMMTIMEOUTS(1000, 1000, 1000, 1000, 1000)
    r = kernel32.SetCommTimeouts(h, ctypes.byref(timeouts))
    print(f"{'[+]' if r else '[!]'} SetCommTimeouts  -> {'OK' if r else f'Error {ctypes.get_last_error()} (lanjut)'}")

    # Step 3: SetCommMask
    r = kernel32.SetCommMask(h, 0x100)
    print(f"{'[+]' if r else '[!]'} SetCommMask      -> {'OK' if r else f'Error {ctypes.get_last_error()} (lanjut)'}")

    # Step 4: GetCommState -> ambil DCB saat ini
    dcb = DCB()
    dcb.DCBlength = ctypes.sizeof(DCB)
    r = kernel32.GetCommState(h, ctypes.byref(dcb))
    print(f"{'[+]' if r else '[!]'} GetCommState     -> {'OK' if r else f'Error {ctypes.get_last_error()} (lanjut)'}")

    # Step 5: BuildCommDCBA -> set 4800 8N1
    r = kernel32.BuildCommDCBA(b"baud=4800 parity=N data=8 stop=1", ctypes.byref(dcb))
    print(f"{'[+]' if r else '[-]'} BuildCommDCBA    -> {'OK (4800 8N1 siap)' if r else f'GAGAL Error {ctypes.get_last_error()}'}")

    # Step 6: SetCommState -> terapkan ke hardware (boleh gagal pada CH340 clone)
    r = kernel32.SetCommState(h, ctypes.byref(dcb))
    err = ctypes.get_last_error()
    if r:
        print("[+] SetCommState     -> OK - Port terkonfigurasi sempurna!")
    else:
        print(f"[!] SetCommState     -> GAGAL Error {err} (Mode kompatibilitas chip clone)")
        print("    -> Ini NORMAL untuk chip CH340/Prolific murahan. Data TX tetap berjalan.")

    print("--- [DEBUG SELESAI] ---")
    return h

def send_payload(h, payload_bytes, description):
    """Menembakkan Array Bytes via WriteFile dengan debug log TX."""
    hex_str = ' '.join([f"{b:02X}" for b in payload_bytes])
    print(f"\n[*] Perintah    : {description}")
    print(f"[>] TX Payload  : [ {hex_str} ]")

    buf = (ctypes.c_byte * len(payload_bytes))(*payload_bytes)
    written = ctypes.wintypes.DWORD(0)
    r = kernel32.WriteFile(h, buf, len(payload_bytes), ctypes.byref(written), None)

    if r:
        print(f"[+] WriteFile OK  -> {written.value} byte terkirim ke hardware!")
    else:
        err = ctypes.get_last_error()
        print(f"[-] WriteFile GAGAL! Win32 Error: {err}")
        keterangan = {
            6:  "Handle tidak valid - kabel mungkin terputus sejak koneksi dibuka.",
            87: "Invalid Parameter - port terbuka dalam mode yang salah (harusnya Synchronous).",
        }.get(err, "Error tidak dikenal. Coba cabut-pasang kabel USB lalu restart aplikasi.")
        print(f"    -> {keterangan}")

def create_set_payload(header, value):
    """
    Membangun 5-byte payload protokol DHZ 8200A.
    Algoritma: nilai * 10 -> int -> string 4 digit -> byte ASCII
    Contoh   : 15.5 km/h -> 155 -> '0155' -> [0xA3, 0x30, 0x31, 0x35, 0x35]
    """
    val_int = int(value * 10)
    val_str = f"{val_int:04d}"
    print(f"[*] Kalkulasi  : {value} x 10 = {val_int} -> '{val_str}' (4-digit ASCII)")
    return [header] + [ord(c) for c in val_str]

def main():
    global current_speed, current_grade, is_running, h_port, current_port

    current_port = "NONE"
    print_banner()
    print("Berkomunikasi LANGSUNG via Win32 API (CreateFileA + WriteFile)")
    print("Tanpa DrvtDHZ8200A.dll.\n")

    # === SCAN PORT ===
    ports_info = scan_com_ports()
    if not ports_info:
        print("\n[-] Tidak ada COM Port yang terdeteksi!")
        print("    Pastikan kabel USB Treadmill sudah dicolokkan.")
        input("Tekan Enter untuk keluar..."); return

    print(f"\n[+] Ditemukan {len(ports_info)} port:")
    for i, (dev, desc) in enumerate(ports_info):
        print(f"  [{i+1}] {dev} - {desc}")

    try:
        pilihan = int(input(f"\nPilih nomor port (1-{len(ports_info)}): ").strip()) - 1
        if not (0 <= pilihan < len(ports_info)):
            print("[-] Pilihan di luar jangkauan."); return
    except ValueError:
        print("[-] Input tidak valid."); return

    device_name, device_desc = ports_info[pilihan]
    current_port = device_name
    h_port = open_port(device_name)

    if not h_port:
        print("\n[-] Koneksi gagal. Lihat debug log di atas.")
        input("Tekan Enter untuk keluar..."); return

    print(f"\n[+] SIAP! Terhubung ke {current_port}.")
    input("Tekan Enter untuk masuk ke menu utama...")

    # === MENU UTAMA ===
    while True:
        print_banner()
        print("[1] START (Mulai Belt Treadmill)")
        print("[2] STOP  (Hentikan Belt)")
        print("[3] SET SPEED  (Atur Kecepatan)")
        print("[4] SET GRADE  (Atur Kemiringan)")
        print("[5] BACA DATA  (Get Speed & Grade)")
        print("[0] KELUAR")
        print("-" * 60)

        pilihan = input("Pilihan Anda: ").strip()

        if pilihan == '1':
            send_payload(h_port, [0xA1], "START MOTOR")
            current_speed = 0.0; current_grade = 0.0
            is_running = True
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '2':
            send_payload(h_port, [0xA2], "STOP MOTOR")
            current_speed = 0.0; current_grade = 0.0
            is_running = False
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '3':
            try:
                val = float(input("\nKecepatan (0.0 - 20.0 km/h): "))
                if 0.0 <= val <= 20.0:
                    payload = create_set_payload(0xA3, val)
                    send_payload(h_port, payload, f"SET SPEED {val} km/h")
                    current_speed = val
                else:
                    print("[-] Di luar batas hardware (0.0 - 20.0 km/h)")
            except ValueError:
                print("[-] Format tidak valid. Contoh: 5.5")
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '4':
            try:
                val = float(input("\nKemiringan (0.0 - 24.0 %): "))
                if 0.0 <= val <= 24.0:
                    payload = create_set_payload(0xA4, val)
                    send_payload(h_port, payload, f"SET GRADE {val}%")
                    current_grade = val
                else:
                    print("[-] Di luar batas hardware (0.0 - 24.0 %)")
            except ValueError:
                print("[-] Format tidak valid. Contoh: 2.0")
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '5':
            print(f"\n[+] Data Tersimpan Saat Ini:")
            print(f"    Kecepatan  : {current_speed} km/h")
            print(f"    Kemiringan : {current_grade} %")
            print("    (Catatan: Nilai ini dikelola lokal karena sistem Open-Loop)")
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '0':
            print("\n[*] Menutup port dan keluar...")
            kernel32.CloseHandle(h_port)
            print("[+] Handle ditutup. Selamat tinggal!")
            break
        else:
            print("[-] Pilihan tidak valid.")
            time.sleep(1)

if __name__ == '__main__':
    main()
