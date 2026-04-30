import serial
import time
import sys
import os

# State lokal untuk Open Loop System
current_speed = 0.0
current_grade = 0.0

def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print(" 🚀 DHZ 8200A FULL-NATIVE TREADMILL CONTROLLER")
    print("    [OPEN-LOOP MODE | 100% DLL-FREE]")
    print("=" * 60)
    print(" Status Saat Ini:")
    print(f" > Speed : {current_speed} km/h")
    print(f" > Grade : {current_grade} %")
    print("=" * 60)

def send_payload(ser, payload_bytes, description):
    """Fungsi pembantu untuk menembakkan Array Bytes ke Serial Port dengan Debug Log"""
    hex_str = ' '.join([f"{b:02X}" for b in payload_bytes])
    print(f"\n[*] Mengirim Perintah: {description}")
    print(f"[>] TX Payload (Hex): [ {hex_str} ]")
    
    try:
        ser.write(bytearray(payload_bytes))
        print("[+] SUCCESS: Data terkirim ke Hardware!")
    except Exception as e:
        print(f"[-] ERROR: Gagal mengirim data. Hardware mungkin terputus. Detail: {e}")

def create_set_payload(header, value):
    """
    Mengubah nilai double menjadi payload 5-byte
    Contoh: 12.5 -> 125 -> "0125" -> [Header, 0x30, 0x31, 0x32, 0x35]
    """
    val_int = int(value * 10)
    # Format ke 4 digit string, misal 125 jadi "0125"
    val_str = f"{val_int:04d}"
    
    payload = [header]
    for char in val_str:
        payload.append(ord(char)) # Convert karakter ASCII ke integer byte
        
    return payload

def main():
    global current_speed, current_grade
    
    print_banner()
    print("Aplikasi ini berinteraksi LANGSUNG dengan protokol mesin")
    print("tanpa menggunakan DrvtDHZ8200A.dll.\n")
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("[-] FATAL ERROR: Tidak ada perangkat COM Port yang terdeteksi di Windows!")
        print("    Pastikan kabel USB Treadmill sudah dicolokkan ke PC.")
        input("Tekan Enter untuk keluar...")
        return

    print("Daftar COM Port yang tersedia di PC Anda:")
    for i, p in enumerate(ports):
        print(f"  [{i+1}] {p.device} - {p.description}")
        
    pilihan_port = input(f"\nPilih port Treadmill Anda (1 - {len(ports)}): ").strip()
    try:
        idx = int(pilihan_port) - 1
        if 0 <= idx < len(ports):
            port_name = ports[idx].device
        else:
            print("[-] Pilihan angka di luar jangkauan.")
            return
    except ValueError:
        print("[-] Harap masukkan angka yang valid.")
        return
    
    print(f"\n[*] Mencoba membuka port {port_name}...")
    try:
        # Inisialisasi Serial Port Native (4800, 8N1)
        # Menambahkan dsrdtr=False dan rtscts=False untuk mencegah Error 31 (A device attached to the system is not functioning)
        # pada beberapa driver USB-to-Serial clone/murah di Windows.
        ser = serial.Serial(
            port=port_name,
            baudrate=4800,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )
        print("[+] SUCCESS: Port terbuka sempurna! Treadmill terhubung.")
    except serial.SerialException as e:
        print("\n[-] FATAL ERROR: Gagal membuka Serial Port!")
        print("    " + str(e))
        print("\n[!] PENYELESAIAN MASALAH (TROUBLESHOOTING):")
        print("    1. Pastikan kabel USB-to-Serial menancap kuat.")
        print("    2. Buka 'Device Manager' Windows, pastikan nomor COM benar.")
        print("    3. Jika 'Access is denied', matikan aplikasi lain (atau tab terminal lain) yang sedang menahan COM port ini.")
        return
        
    time.sleep(1) # Beri nafas untuk chip FTDI/Serial stabil

    while True:
        print_banner()
        print("[1] START (Mulai Treadmill)")
        print("[2] STOP (Berhentikan Perlahan)")
        print("[3] SET SPEED (Atur Kecepatan)")
        print("[4] SET GRADE (Atur Kemiringan)")
        print("[0] KELUAR")
        print("-" * 60)
        
        pilihan = input("Masukkan angka pilihan Anda: ").strip()
        
        if pilihan == '1':
            send_payload(ser, [0xA1], "START MOTOR")
            current_speed = 0.0 # Treadmill DHZ otomatis reset ke 0 saat start
            current_grade = 0.0
            input("\nTekan Enter untuk kembali...")
            
        elif pilihan == '2':
            send_payload(ser, [0xA2], "STOP MOTOR (Deselerasi)")
            current_speed = 0.0
            current_grade = 0.0
            input("\nTekan Enter untuk kembali...")
            
        elif pilihan == '3':
            val_input = input("\nMasukkan kecepatan (0.0 - 20.0 km/h): ")
            try:
                val = float(val_input)
                if 0.0 <= val <= 20.0:
                    payload = create_set_payload(0xA3, val)
                    send_payload(ser, payload, f"SET SPEED ke {val} km/h")
                    current_speed = val
                else:
                    print("[-] Error: Kecepatan harus di antara 0.0 dan 20.0")
            except ValueError:
                print("[-] Error: Masukkan format angka yang valid (contoh: 5.5)")
            input("\nTekan Enter untuk kembali...")
            
        elif pilihan == '4':
            val_input = input("\nMasukkan kemiringan (0.0 - 24.0 %): ")
            try:
                val = float(val_input)
                if 0.0 <= val <= 24.0:
                    payload = create_set_payload(0xA4, val)
                    send_payload(ser, payload, f"SET GRADE ke {val} %")
                    current_grade = val
                else:
                    print("[-] Error: Kemiringan harus di antara 0.0 dan 24.0")
            except ValueError:
                print("[-] Error: Masukkan format angka yang valid (contoh: 2.0)")
            input("\nTekan Enter untuk kembali...")
            
        elif pilihan == '0':
            print("\n[*] Menutup port Serial dan keluar...")
            ser.close()
            print("[+] Aplikasi ditutup dengan aman.")
            break
        else:
            print("[-] Pilihan tidak valid.")
            time.sleep(1)

if __name__ == '__main__':
    main()
