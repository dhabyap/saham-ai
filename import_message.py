import json
import sqlite3
import os

filepath = r'C:\Users\dhaby\AppData\Local\hermes\cache\documents\doc_2d424e4884fe_message.txt'
dbpath = r'D:\Latihan\Saham\analisa-saham\app\database\stock.db'

def import_data():
    if not os.path.exists(filepath):
        print("File tidak ditemukan")
        return

    with open(filepath, 'r') as f:
        for line in f:
            if line.startswith('1:'):
                try:
                    data = json.loads(line[2:])
                    ticker = data.get('ticker')
                    summary = data.get('broker_summary', {})
                    buyers = summary.get('buyers', [])
                    
                    conn = sqlite3.connect(dbpath)
                    cur = conn.cursor()
                    
                    cur.execute('DELETE FROM broker_summary WHERE stock_code = ?', (ticker,))
                    
                    for b in buyers:
                        cur.execute('''
                            INSERT INTO broker_summary (stock_code, broker_code, side, lots, value, avg_price)
                            VALUES (?, ?, 'BUY', ?, ?, ?)
                        ''', (ticker, b['broker_code'], b['lots'], b['value'], b['avg_price']))
                    
                    conn.commit()
                    conn.close()
                    print(f"Berhasil import {len(buyers)} data broker untuk {ticker}")
                    return
                except Exception as e:
                    print(f"Error import: {e}")

if __name__ == "__main__":
    import_data()
