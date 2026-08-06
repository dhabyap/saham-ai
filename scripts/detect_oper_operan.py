import mysql.connector
import sys

def detect_churning(stock_code, period_start, period_end):
    # Koneksi ke DB
    db = mysql.connector.connect(host="127.0.0.1", user="root", password="", database="analisa_saham")
    cursor = db.cursor(dictionary=True)

    # 1. Cari broker top buyer dan top seller
    query = f"""
    SELECT broker_code, side, SUM(value) as total_val, SUM(lots) as total_lots, 
           (SUM(value)/NULLIF(SUM(lots), 0)) as avg_price
    FROM broker_summary
    WHERE stock_code = '{stock_code}' 
      AND period_from >= '{period_start}' 
      AND period_to <= '{period_end}'
    GROUP BY broker_code, side
    ORDER BY total_val DESC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    
    # Deteksi oper-operan:
    # Syarat: Ada broker yang jual/beli dengan volume masif dan avg price yang mencolok
    print(f"--- ANALISA OPER-OPERAN: {stock_code} ---")
    for row in results:
        avg_price_str = f"{row['avg_price']:.2f}" if row['avg_price'] is not None else "N/A"
        print(f"Broker: {row['broker_code']} | {row['side'].upper()} | Value: {row['total_val']/1e9:.2f}B | Avg: {avg_price_str}")

    db.close()

if __name__ == "__main__":
    detect_churning(sys.argv[1], sys.argv[2], sys.argv[3])
