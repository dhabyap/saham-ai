import json
import mysql.connector
import os

filepath = r'C:\Users\dhaby\AppData\Local\hermes\cache\documents\doc_2d424e4884fe_message.txt'

def import_data():
    if not os.path.exists(filepath):
        print("File tidak ditemukan")
        return

    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='analisa_saham'
        )
        cur = conn.cursor()

        with open(filepath, 'r') as f:
            for line in f:
                if line.startswith('1:'):
                    data = json.loads(line[2:])
                    ticker = data.get('ticker')
                    summary = data.get('broker_summary', {})
                    buyers = summary.get('buyers', [])
                    
                    # Clean old data
                    cur.execute('DELETE FROM broker_summary WHERE stock_code = %s', (ticker,))
                    
                    # Bulk insert
                    sql = "INSERT INTO broker_summary (stock_code, broker_code, side, lots, value, avg_price) VALUES (%s, %s, %s, %s, %s, %s)"
                    vals = [(ticker, b['broker_code'], 'BUY', b['lots'], b['value'], b['avg_price']) for b in buyers]
                    cur.executemany(sql, vals)
                    
                    conn.commit()
                    print(f"Berhasil import {len(buyers)} data broker ke MySQL untuk {ticker}")
                    break
        conn.close()
    except Exception as e:
        print(f"Error MySQL: {e}")

if __name__ == "__main__":
    import_data()
