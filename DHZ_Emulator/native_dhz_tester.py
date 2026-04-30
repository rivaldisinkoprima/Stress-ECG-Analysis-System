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
h_port = None
current_port = 0

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    status_port = f"COM{current_port}" if h_port else "TERPUTUS"
    print("=" * 60)
    print(" ========================================")
    print(" DHZ 8200A FULL-NATIVE TREADMILL CONTROLLER")
    print(" [OPEN-LOOP | 100% DLL-FREE | RAW WIN32 API]")
    print(" ========================================")
    print(f" Port   : {status_port}")
    print(f" Speed  : {current_speed} km/h")
    print(f" Grade  : {current_grade} %")
    print("=" * 60)

def scan_com_ports():
    """Scan COM1-COM29 dengan mencoba CreateFileA ke setiap port."""
    print("[*] Memindai COM Port (COM1 - COM29)...")
    available = []
    INVALID_HANDLE = ctypes.wintypes.HANDLE(-1).value
    for i in range(1, 30):
        port_path = f"\\\\.\\COM{i}".encode('ascii')
        h = kernel32.CreateFileA(port_path, 0xC0000000, 0, None, 3, 0, None)
        if h != INVALID_HANDLE and h != 0:
            available.append(i)
            kernel32.CloseHandle(h)
        else:
            err = ctypes.get_last_error()
            # Error 5 = Access Denied: port ADA tapi dikunci -> tetap masuk list
            if err == 5:
                available.append(i)
    return available

def open_port(port_num):
    """
    Membuka dan mengkonfigurasi COM Port via Win32 API langsung.
    SetCommState yang gagal (Error 31 pada CH340) diabaikan secara sengaja,
    karena chip clone tetap bisa menerima data walaupun konfigurasi ditolak.
    """
    port_path = f"\\\\.\\COM{port_num}".encode('ascii')
    INVALID_HANDLE = ctypes.wintypes.HANDLE(-1).value

    print(f"\n--- [DEBUG] Membuka \\\\.\\COM{port_num} ---")

    # Step 1: CreateFileA
    h = kernel32.CreateFileA(
        port_path,
        0xC0000000,   # GENERIC_READ | GENERIC_WRITE
        0,            # No sharing
        None,
        3,            # OPEN_EXISTING
        0x40000000,   # FILE_FLAG_OVERLAPPED
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
        if err == 6:
            print("    -> Handle tidak valid. Kabel mungkin terputus sejak koneksi dibuka.")
        else:
            print("    -> Coba cabut dan pasang ulang kabel USB, lalu restart aplikasi.")

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
    global current_speed, current_grade, h_port, current_port

    print_banner()
    print("Berkomunikasi LANGSUNG via Win32 API (CreateFileA + WriteFile)")
    print("Tanpa PySerial dan tanpa DrvtDHZ8200A.dll.\n")

    # === SCAN PORT ===
    ports = scan_com_ports()
    if not ports:
        print("\n[-] Tidak ada COM Port yang terdeteksi!")
        print("    Pastikan kabel USB Treadmill sudah dicolokkan.")
        input("Tekan Enter untuk keluar..."); return

    print(f"\n[+] Ditemukan {len(ports)} port:")
    for i, p in enumerate(ports):
        print(f"  [{i+1}] COM{p}")

    try:
        pilihan = int(input(f"\nPilih nomor port (1-{len(ports)}): ").strip()) - 1
        if not (0 <= pilihan < len(ports)):
            print("[-] Pilihan di luar jangkauan."); return
    except ValueError:
        print("[-] Input tidak valid."); return

    current_port = ports[pilihan]
    h_port = open_port(current_port)

    if not h_port:
        print("\n[-] Koneksi gagal. Lihat debug log di atas.")
        input("Tekan Enter untuk keluar..."); return

    print(f"\n[+] SIAP! Terhubung ke COM{current_port}.")
    input("Tekan Enter untuk masuk ke menu utama...")

    # === MENU UTAMA ===
    while True:
        print_banner()
        print("[1] START (Mulai Belt Treadmill)")
        print("[2] STOP  (Hentikan Belt)")
        print("[3] SET SPEED  (Atur Kecepatan)")
        print("[4] SET GRADE  (Atur Kemiringan)")
        print("[0] KELUAR")
        print("-" * 60)

        pilihan = input("Pilihan Anda: ").strip()

        if pilihan == '1':
            send_payload(h_port, [0xA1], "START MOTOR")
            current_speed = 0.0; current_grade = 0.0
            input("\nTekan Enter untuk kembali...")

        elif pilihan == '2':
            send_payload(h_port, [0xA2], "STOP MOTOR")
            current_speed = 0.0; current_grade = 0.0
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
