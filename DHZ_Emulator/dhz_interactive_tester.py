import ctypes
import sys
import time

def clear_screen():
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("=" * 60)
    print("🚀 DHZ 8200A TREADMILL INTERACTIVE TESTER (WRAPPER) 🚀")
    print("=" * 60)

    # 1. Pengecekan arsitektur Python
    is_64bits = sys.maxsize > 2**32
    if is_64bits:
        print("\n[ERROR CRITICAL] Anda menggunakan Python 64-bit!")
        print("DLL 'DrvtDHZ8200A.dll' dikompilasi menggunakan arsitektur 32-bit (x86).")
        print("Silakan install dan gunakan Python 32-bit untuk menjalankan script ini.")
        input("\nTekan Enter untuk keluar...")
        sys.exit(1)

    print("[*] Sistem arsitektur Python (32-bit) valid.")

    # 2. Meload DLL
    try:
        print("[*] Mencoba memuat driver DrvtDHZ8200A.dll...")
        # Mencoba CDLL (Standar cdecl untuk C++ Native)
        try:
            dhz = ctypes.CDLL("./DrvtDHZ8200A.dll")
        except ValueError:
            # Jika gagal, mungkin menggunakan stdcall
            dhz = ctypes.WinDLL("./DrvtDHZ8200A.dll")
            
        print("[*] BERHASIL! DLL DrvtDHZ8200A.dll telah ter-load ke memori.")
    except Exception as e:
        print(f"\n[ERROR] Gagal meload DLL. Pastikan file 'DrvtDHZ8200A.dll' berada di folder yang sama.")
        print(f"Detail error: {e}")
        input("\nTekan Enter untuk keluar...")
        sys.exit(1)

    # 3. Mendaftarkan Tipe Data Argumen (Sangat Penting untuk Floating Point)
    try:
        dhz.DrvConnect.argtypes = [ctypes.c_int]
        dhz.DrvSetSpeed.argtypes = [ctypes.c_double]
        dhz.DrvSetGrade.argtypes = [ctypes.c_double]
        
        # Fungsi Get mengembalikan double
        dhz.DrvGetSpeed.restype = ctypes.c_double
        dhz.DrvGetGrade.restype = ctypes.c_double
    except Exception as e:
        print(f"\n[WARNING] Beberapa fungsi mungkin tidak tersedia di versi DLL ini: {e}")

    time.sleep(1)
    
    # 4. Interactive Loop
    connected = False
    
    while True:
        clear_screen()
        print("=" * 50)
        print("   PANEL KONTROL TREADMILL DHZ 8200A   ")
        print("=" * 50)
        status = "TERHUBUNG" if connected else "TERPUTUS"
        print(f"Status Saat Ini : [{status}]\n")
        
        print("[1] Buka Koneksi (Connect Port)")
        print("[2] Kirim Perintah START (Jalankan Mesin)")
        print("[3] Kirim Perintah STOP (Berhentikan Mesin)")
        print("[4] Atur Kecepatan (Set Speed)")
        print("[5] Atur Kemiringan (Set Incline/Grade)")
        print("[6] Baca Kecepatan Saat Ini (Get Speed)")
        print("[7] Baca Kemiringan Saat Ini (Get Grade)")
        print("[8] Putus Koneksi (Disconnect)")
        print("[0] Keluar Aplikasi")
        print("-" * 50)
        
        pilihan = input("Masukkan angka pilihan Anda: ")
        
        try:
            if pilihan == '1':
                if connected:
                    print("\n[INFO] Treadmill sudah terhubung!")
                else:
                    port = int(input("\nMasukkan nomor COM Port (misal: 4 untuk COM4): "))
                    print(f"[*] Menghubungkan ke COM{port}...")
                    # DLL mengeksekusi CreateFileA dan BuildCommDCB di background
                    result = dhz.DrvConnect(port)
                    # Result 1 biasanya success, 0 false
                    print(f"[*] Perintah DrvConnect dikirim! (Return code: {result})")
                    connected = True
                    print("[+] Sukses membuka jalur komunikasi.")

            elif pilihan == '2':
                if not connected:
                    print("\n[WARNING] Harap Connect Port (1) terlebih dahulu!")
                else:
                    print("\n[*] Mengirim command START...")
                    dhz.DrvStart()
                    print("[+] Command terkirim. Belt treadmill seharusnya mulai bergerak.")

            elif pilihan == '3':
                if not connected:
                    print("\n[WARNING] Harap Connect Port (1) terlebih dahulu!")
                else:
                    print("\n[*] Mengirim command STOP...")
                    dhz.DrvStop()
                    print("[+] Command terkirim. Belt treadmill akan melambat dan berhenti.")

            elif pilihan == '4':
                if not connected:
                    print("\n[WARNING] Harap Connect Port (1) terlebih dahulu!")
                else:
                    speed = float(input("\nMasukkan kecepatan (misal: 5.5) [Max 20.0]: "))
                    if speed < 0 or speed > 20.0:
                        print("[ERROR] Nilai kecepatan di luar batas aman (0 - 20.0)!")
                    else:
                        print(f"[*] Menerjemahkan angka {speed} menjadi Hex dan mengirim ke alat...")
                        dhz.DrvSetSpeed(speed)
                        print("[+] Command kecepatan terkirim.")

            elif pilihan == '5':
                if not connected:
                    print("\n[WARNING] Harap Connect Port (1) terlebih dahulu!")
                else:
                    grade = float(input("\nMasukkan kemiringan (misal: 2.0) [Max 24.0]: "))
                    if grade < 0 or grade > 24.0:
                        print("[ERROR] Nilai kemiringan di luar batas aman (0 - 24.0)!")
                    else:
                        print(f"[*] Menerjemahkan angka {grade} menjadi Hex dan mengirim ke alat...")
                        dhz.DrvSetGrade(grade)
                        print("[+] Command kemiringan terkirim.")

            elif pilihan == '6':
                if not connected:
                    print("\n[WARNING] Harap Connect Port (1) terlebih dahulu!")
                else:
                    print("\n[*] Membaca kecepatan dari alat...")
                    current_speed = dhz.DrvGetSpeed()
                    print(f"[+] Kecepatan Treadmill saat ini: {current_speed} km/h")

            elif pilihan == '7':
                if not connected:
                    print("\n[WARNING] Harap Connect Port (1) terlebih dahulu!")
                else:
                    print("\n[*] Membaca kemiringan dari alat...")
                    current_grade = dhz.DrvGetGrade()
                    print(f"[+] Kemiringan (Incline) saat ini: {current_grade}")

            elif pilihan == '8':
                if not connected:
                    print("\n[INFO] Belum ada koneksi yang terbuka.")
                else:
                    print("\n[*] Memutus jalur Serial Port...")
                    dhz.DrvDisconnect()
                    connected = False
                    print("[+] Koneksi terputus dengan aman.")

            elif pilihan == '0':
                if connected:
                    print("\n[*] Memutus koneksi sebelum keluar...")
                    dhz.DrvDisconnect()
                print("\nKeluar dari aplikasi tester. Sampai jumpa!")
                sys.exit(0)
            
            else:
                print("\n[ERROR] Pilihan tidak valid!")
                
        except ValueError:
            print("\n[ERROR] Input harus berupa angka yang benar!")
        except Exception as e:
            print(f"\n[ERROR FATAL] Terjadi kesalahan saat memanggil fungsi DLL: {e}")
            
        input("\nTekan Enter untuk kembali ke Menu Utama...")

if __name__ == '__main__':
    main()
