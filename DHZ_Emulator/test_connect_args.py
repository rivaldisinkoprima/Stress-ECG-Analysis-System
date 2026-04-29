import ctypes
import sys

def main():
    print("[*] Menguji Hipotesis Parameter Ganda pada DrvConnect...")
    
    try:
        dhz = ctypes.CDLL("./DrvtDHZ8200A.dll", use_last_error=True)
    except Exception as e:
        print(f"[-] Gagal memuat DLL: {e}")
        return

    # Kita ubah argtypes menjadi DUA integer!
    # Arg1: Dummy/Context (0)
    # Arg2: COM Port yang sebenarnya
    dhz.DrvConnect.argtypes = [ctypes.c_int, ctypes.c_int]
    dhz.DrvConnect.restype = ctypes.c_int
    
    port = 15
    print(f"[*] Memanggil DrvConnect(0, {port})...")
    
    result = dhz.DrvConnect(0, port)
    
    if result == 1:
        print(f"[+] BINGO! Hipotesis BENAR. Koneksi SUKSES! (Return: {result})")
        # Putus koneksi agar bersih
        dhz.DrvDisconnect()
    else:
        err = ctypes.get_last_error()
        print(f"[-] MASIH GAGAL! (Return: {result})")
        print(f"[-] Error Code: {err}")

if __name__ == '__main__':
    main()
