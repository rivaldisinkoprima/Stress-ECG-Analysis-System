import ctypes
import ctypes.wintypes
import sys
import os

kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

class COMMTIMEOUTS(ctypes.Structure):
    _fields_ = [
        ("ReadIntervalTimeout", ctypes.wintypes.DWORD),
        ("ReadTotalTimeoutMultiplier", ctypes.wintypes.DWORD),
        ("ReadTotalTimeoutConstant", ctypes.wintypes.DWORD),
        ("WriteTotalTimeoutMultiplier", ctypes.wintypes.DWORD),
        ("WriteTotalTimeoutConstant", ctypes.wintypes.DWORD),
    ]

class DCB(ctypes.Structure):
    _fields_ = [
        ("DCBlength", ctypes.wintypes.DWORD), ("BaudRate", ctypes.wintypes.DWORD),
        ("Flags", ctypes.wintypes.DWORD), ("wReserved", ctypes.wintypes.WORD),
        ("XonLim", ctypes.wintypes.WORD), ("XoffLim", ctypes.wintypes.WORD),
        ("ByteSize", ctypes.c_byte), ("Parity", ctypes.c_byte),
        ("StopBits", ctypes.c_byte), ("XonChar", ctypes.c_char),
        ("XoffChar", ctypes.c_char), ("ErrorChar", ctypes.c_char),
        ("EofChar", ctypes.c_char), ("EvtChar", ctypes.c_char),
        ("wReserved1", ctypes.wintypes.WORD),
    ]

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("=" * 60)
    print("🚀 DHZ 8200A TREADMILL - THE ULTIMATE BYPASS MODE 🚀")
    print("=" * 60)

    try:
        dhz = ctypes.CDLL("./DrvtDHZ8200A.dll", use_last_error=True)
        hmod = kernel32.GetModuleHandleA(b"DrvtDHZ8200A.dll")
    except Exception as e:
        print(f"[-] Gagal memuat DLL: {e}")
        sys.exit(1)

    dhz.DrvSetSpeed.argtypes = [ctypes.c_double]
    dhz.DrvSetGrade.argtypes = [ctypes.c_double]
    dhz.DrvGetSpeed.restype = ctypes.c_double
    dhz.DrvGetGrade.restype = ctypes.c_double
    
    connected = False
    
    while True:
        clear_screen()
        status = "TERHUBUNG (ULTIMATE BYPASS)" if connected else "TERPUTUS"
        print(f"Status Saat Ini : [{status}]\n")
        print("[1] Buka Koneksi (Ultimate Bypass)")
        print("[2] Kirim Perintah START")
        print("[3] Kirim Perintah STOP")
        print("[4] Atur Kecepatan (Set Speed)")
        print("[5] Atur Kemiringan (Set Grade)")
        print("[6] Baca Data (Get Speed & Grade)")
        print("[0] Keluar Aplikasi\n")
        
        pilihan = input("Masukkan angka pilihan Anda: ")
        
        try:
            if pilihan == '1':
                port = int(input("\nMasukkan nomor COM Port (misal: 15): "))
                
                # 1. Pancing DLL untuk membentuk struktur Event di memori
                print("[*] Memancing inisialisasi DLL...")
                try:
                    dhz.DrvConnect(port)
                except Exception:
                    pass
                
                # 2. Dapatkan Global Object Pointer
                obj_ptr_addr = hmod + 0x45ec
                obj_ptr = ctypes.cast(obj_ptr_addr, ctypes.POINTER(ctypes.c_uint32))[0]
                
                if obj_ptr == 0:
                    print("[-] FATAL: Object DLL gagal terbentuk!")
                    input(); continue
                
                # 3. Buka Port Secara Paksa dari Python
                print(f"[*] Mengambil alih kontrol COM{port} secara manual...")
                port_name = f"\\\\.\\COM{port}".encode('ascii')
                handle = kernel32.CreateFileA(port_name, 0xC0000000, 0, None, 3, 0x40000000, None)
                
                if handle == -1 or handle == 0:
                    print(f"[-] GAGAL merebut Port! Error: {ctypes.get_last_error()}")
                    print("    Pastikan kabel dicolok dan tidak dikunci aplikasi lain.")
                    input(); continue
                
                # 4. Konfigurasi Standar DHZ 8200A
                print("[*] Menulis konfigurasi Baud Rate & Timeouts...")
                kernel32.SetCommTimeouts(handle, ctypes.byref(COMMTIMEOUTS(1000, 1000, 1000, 1000, 1000)))
                kernel32.SetCommMask(handle, 0x100)
                dcb = DCB()
                dcb.DCBlength = ctypes.sizeof(DCB)
                kernel32.GetCommState(handle, ctypes.byref(dcb))
                kernel32.BuildCommDCBA(b"baud=4800 parity=N data=8 stop=1", ctypes.byref(dcb))
                kernel32.SetCommState(handle, ctypes.byref(dcb))
                
                # 5. Injeksi Handle ke Otak DLL
                print("[*] Menginjeksi Handle Port ke dalam memori DLL...")
                ctypes.cast(obj_ptr + 0x28, ctypes.POINTER(ctypes.c_uint32))[0] = handle
                
                # 6. Hidupkan Thread Pekerja secara paksa
                print("[*] Me-restart paksa Thread Detak Jantung Treadmill...")
                THREAD_START_ROUTINE = ctypes.WINFUNCTYPE(ctypes.wintypes.DWORD, ctypes.c_void_p)
                thread_func = THREAD_START_ROUTINE(hmod + 0x1c90)
                
                thread_handle = kernel32.CreateThread(None, 0, thread_func, obj_ptr, 0, None)
                
                if thread_handle:
                    connected = True
                    print("\n[+] BOOM! ULTIMATE BYPASS SUKSES!")
                    print("[+] Silakan tekan Enter dan coba jalankan (START) Treadmill-nya.")
                else:
                    print("[-] Gagal menyalakan thread.")
                    
            elif pilihan == '2':
                if connected:
                    dhz.DrvStart()
                    print("[+] Perintah START masuk ke memori. Belt harusnya mulai bergerak...")
                else: print("Connect dulu!")
            elif pilihan == '3':
                if connected: dhz.DrvStop()
            elif pilihan == '4':
                if connected:
                    speed = float(input("\nMasukkan kecepatan (misal: 1.5): "))
                    dhz.DrvSetSpeed(speed)
                    print(f"[+] Kecepatan di-set ke {speed}")
            elif pilihan == '5':
                if connected:
                    grade = float(input("\nMasukkan kemiringan (misal: 2.0): "))
                    dhz.DrvSetGrade(grade)
                    print(f"[+] Kemiringan di-set ke {grade}")
            elif pilihan == '6':
                if connected:
                    print(f"[+] Kecepatan: {dhz.DrvGetSpeed()} km/h | Kemiringan: {dhz.DrvGetGrade()}")
                else: print("Connect dulu!")
            elif pilihan == '0':
                sys.exit(0)
                
        except Exception as e:
            print(f"[-] Error: {e}")
            
        input("\nTekan Enter untuk lanjut...")

if __name__ == '__main__':
    main()
