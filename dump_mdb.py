import pyodbc

db_file = r'F:\val\ECG8000S\Stress ECG Analysis System\StressECG.mdb'
conn_str = f'Driver={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={db_file};PWD=aboutface;'

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    tables = ['Cases', 'Protocols']
    
    for table in tables:
        print(f"\n--- COLUMNS IN {table} ---")
        try:
            for row in cursor.columns(table=table):
                print(f"{row.column_name} ({row.type_name})")
        except Exception as e:
            print(f"Error reading {table}: {e}")
            
    conn.close()
except Exception as e:
    print(f"Error: {e}")
