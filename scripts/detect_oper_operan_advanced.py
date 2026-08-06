import mysql.connector
import sys
from collections import defaultdict

# Broker mapping from memory
BROKER_MAPPING = {
    'AK': 'UBS',
    'ZP': 'Maybank',
    'KZ': 'CLSA',
    'BB': 'Verdhana',
    'CP': 'Valbury',
    'AI': 'UOB Kay Hian',
    'LG': 'Trimegah',
    'PD': 'Indo Premier',
    'NI': 'BNI Sekuritas',
    'CC': 'Mandiri Sekuritas',
    'SQ': 'BCA Sekuritas',
    'DX': 'Bahana Sekuritas',
    'YP': 'Mirae Asset Sekuritas Indonesia',
    'DR': 'RHB Sekuritas Indonesia',
    'BK': 'J.P. Morgan Sekuritas Indonesia',
    'AZ': 'Sucor Sekuritas',
    'SS': 'Samuel Sekuritas Indonesia',
    'YU': 'CGS-CIMB SEKURITAS INDONESIA',
    'XL': 'MAHAKARYA ARTHA SEKURITAS',
    'JB': 'JP Morgan',
    'II': 'Indo Premier', # Reconfirming based on user memory
    'YJ': 'Lotus Andalan Sekuritas',
    'OK': 'NET SEKURITAS',
    'TP': 'OCBC SEKURITAS INDONESIA',
    'OD': 'BRI DANAREKSA SEKURITAS',
    'IF': 'Samuel Sekuritas Indonesia', # Reconfirming based on user memory
    'XC': 'AJAIB SEKURITAS ASIA',
    'DH': 'SINARMAS SEKURITAS',
    'IN': 'Indo Capital Sekuritas',
    'MG': 'SEMESTA INDOVEST SEKURITAS',
    'DP': 'DANATAMA MAKMUR SEKURITAS',
    'GR': 'PANIN SEKURITAS TBK.',
    'EP': 'MNC SEKURITAS',
    'RF': 'BUANA CAPITAL SEKURITAS',
    'AG': 'KIWOOM SEKURITAS INDONESIA',
    'KK': 'PHILLIP SEKURITAS INDONESIA',
    'YB': 'JASA UTAMA CAPITAL SEKURITAS',
    'HP': 'HENAN PUTIHRAI SEKURITAS',
    'RX': 'Reliance Sekuritas Indonesia', # Reconfirming based on user memory
    'PF': 'Panin Financial',
    'CD': 'MEGA CAPITAL SEKURITAS',
    'FS': 'YUANTA SEKURITAS INDONESIA',
    'HD': 'KGI SEKURITAS INDONESIA',
    'RS': 'Reliance Sekuritas Indonesia', # Reconfirming based on user memory
    'IH': 'PACIFIC 2000 SEKURITAS',
    'AO': 'ERDIKHA ELIT SEKURITAS',
    'AT': 'PHINTRACO SEKURITAS',
    'BQ': 'KOREA INVESTMENT AND SEKURITAS INDONESIA',
    'RG': 'PROFINDO SEKURITAS INDONESIA',
    'BS': 'EQUITY SEKURITAS INDONESIA',
    'SA': 'BOSOWA SEKURITAS',
    'KI': 'CIPTADANA SEKURITAS ASIA',
    'LS': 'RELIANCE SEKURITAS INDONESIA TBK.', # Reconfirming based on user memory
    'AF': 'ARTHA SEKURITAS INDONESIA',
    'RO': 'NILAI INTI SEKURITAS',
    'BF': 'Bahana Sekuritas', # Reconfirming based on user memory
    'ZR': 'BUMIPUTERA SEKURITAS',
    'AH': 'ASAHAN ANDALAS SEKURITAS',
    'PC': 'FAC SEKURITAS INDONESIA',
    'XA': 'NH KORINDO SEKURITAS INDONESIA',
    'PG': 'PANCA GLOBAL SEKURITAS',
    'MU': 'MINNA PADI INVESTAMA SEKURITAS TBK',
    'ID': 'ANUGERAH SEKURITAS INDONESIA',
    'YO': 'YUANTA SEKURITAS INDONESIA', # Reconfirming based on user memory
    'MI': 'VICTORIA SEKURITAS INDONESIA',
    'SH': 'ARTHA SEKURITAS INDONESIA', # Reconfirming based on user memory
    'ES': 'EKOKAPITAL SEKURITAS',
    'IT': 'Investindo Nusantara Sekuritas',
    'PP': 'PANIN SEKURITAS TBK.', # Reconfirming based on user memory
    'SF': 'SURYA FAJAR SEKURITAS',
    'AR': 'BINAARTHA SEKURITAS',
    'RB': 'NIKKO SEKURITAS INDONESIA',
    'QA': 'Tuntun Sekuritas Indonesia',
    'PO': 'PILARMAS INVESTINDO SEKURITAS', # Reconfirming based on user memory
    'EL': 'EKAJAYA INTRA SEKURITAS',
    'PI': 'Premiere Sekuritas Indonesia',
    'TF': 'UNIVERSAL BROKER INDONESIA SEKURITAS',
    'BR': 'TRUST SEKURITAS', # Reconfirming based on user memory
    'DU': 'DANAREKSA SEKURITAS',
    'GA': 'GANESHA REKSA SEKURITAS',
    'AD': 'ADITAMA SEKURITAS',
    'GI': 'GLOBALINDO INVESTAMA PRATAMA',
    'FZ': 'WATERFRONT SEKURITAS INDONESIA',
}

# Categorization based on common knowledge/memory (can be expanded)
BROKER_CATEGORY = {
    'UBS': 'FOREIGN', 'Maybank': 'FOREIGN', 'CLSA': 'FOREIGN', 'UOB Kay Hian': 'FOREIGN', 'Trimegah': 'FOREIGN',
    'Indo Premier': 'LOCAL', 'Verdhana': 'LOCAL', 'Valbury': 'LOCAL', 'BNI Sekuritas': 'BUMN', 'Mandiri Sekuritas': 'BUMN',
    'BCA Sekuritas': 'LOCAL', 'Bahana Sekuritas': 'BUMN', 'Mirae Asset Sekuritas Indonesia': 'FOREIGN',
    'RHB Sekuritas Indonesia': 'FOREIGN', 'J.P. Morgan Sekuritas Indonesia': 'FOREIGN', 'Sucor Sekuritas': 'LOCAL',
    'Samuel Sekuritas Indonesia': 'LOCAL', 'CGS-CIMB SEKURITAS INDONESIA': 'FOREIGN', 'MAHAKARYA ARTHA SEKURITAS': 'LOCAL',
    'JP Morgan': 'FOREIGN', 'Lotus Andalan Sekuritas': 'LOCAL', 'NET SEKURITAS': 'LOCAL', 'OCBC SEKURITAS INDONESIA': 'FOREIGN',
    'BRI DANAREKSA SEKURITAS': 'BUMN', 'AJAIB SEKURITAS ASIA': 'LOCAL', 'SINARMAS SEKURITAS': 'LOCAL',
    'Indo Capital Sekuritas': 'LOCAL', 'SEMESTA INDOVEST SEKURITAS': 'LOCAL', 'DANATAMA MAKMUR SEKURITAS': 'LOCAL',
    'PANIN SEKURITAS TBK.': 'LOCAL', 'MNC SEKURITAS': 'LOCAL', 'BUANA CAPITAL SEKURITAS': 'LOCAL',
    'KIWOOM SEKURITAS INDONESIA': 'FOREIGN', 'PHILLIP SEKURITAS INDONESIA': 'FOREIGN', 'JASA UTAMA CAPITAL SEKURITAS': 'LOCAL',
    'HENAN PUTIHRAI SEKURITAS': 'LOCAL', 'Reliance Sekuritas Indonesia': 'FOREIGN', 'Panin Financial': 'LOCAL',
    'MEGA CAPITAL SEKURITAS': 'LOCAL', 'YUANTA SEKURITAS INDONESIA': 'FOREIGN', 'KGI SEKURITAS INDONESIA': 'FOREIGN',
    'PACIFIC 2000 SEKURITAS': 'LOCAL', 'ERDIKHA ELIT SEKURITAS': 'LOCAL', 'PHINTRACO SEKURITAS': 'LOCAL',
    'KOREA INVESTMENT AND SEKURITAS INDONESIA': 'FOREIGN', 'PROFINDO SEKURITAS INDONESIA': 'LOCAL', 'EQUITY SEKURITAS INDONESIA': 'LOCAL',
    'BOSOWA SEKURITAS': 'LOCAL', 'CIPTADANA SEKURITAS ASIA': 'LOCAL', 'ARTHA SEKURITAS INDONESIA': 'LOCAL',
    'NILAI INTI SEKURITAS': 'LOCAL', 'BUMIPUTERA SEKURITAS': 'LOCAL', 'ASAHAN ANDALAS SEKURITAS': 'LOCAL',
    'FAC SEKURITAS INDONESIA': 'LOCAL', 'NH KORINDO SEKURITAS INDONESIA': 'FOREIGN', 'PANCA GLOBAL SEKURITAS': 'LOCAL',
    'MINNA PADI INVESTAMA SEKURITAS TBK': 'LOCAL', 'ANUGERAH SEKURITAS INDONESIA': 'LOCAL', 'VICTORIA SEKURITAS INDONESIA': 'LOCAL',
    'EKOKAPITAL SEKURITAS': 'LOCAL', 'Investindo Nusantara Sekuritas': 'LOCAL', 'Tuntun Sekuritas Indonesia': 'LOCAL',
    'UNIVERSAL BROKER INDONESIA SEKURITAS': 'LOCAL', 'TRUST SEKURITAS': 'LOCAL', 'DANAREKSA SEKURITAS': 'BUMN',
    'GANESHA REKSA SEKURITAS': 'LOCAL', 'ADITAMA SEKURITAS': 'LOCAL', 'GLOBALINDO INVESTAMA PRATAMA': 'LOCAL',
    'WATERFRONT SEKURITAS INDONESIA': 'LOCAL', 'EKAJAYA INTRA SEKURITAS': 'LOCAL', 'Premiere Sekuritas Indonesia': 'LOCAL',
    'NIKKO SEKURITAS INDONESIA': 'FOREIGN', 'PILARMAS INVESTINDO SEKURITAS': 'LOCAL'
}


def detect_churning_advanced(stock_code, period_start, period_end):
    db = mysql.connector.connect(host="127.0.0.1", user="root", password="", database="analisa_saham")
    cursor = db.cursor(dictionary=True)

    query = f"""
    SELECT stock_code, broker_code, side, SUM(lots) as total_lots, SUM(value) as total_val, 
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
    db.close()

    if not results:
        print(f"Tidak ada data untuk {stock_code} periode {period_start} hingga {period_end}.")
        return

    buy_data = [row for row in results if row['side'] == 'buy']
    sell_data = [row for row in results if row['side'] == 'sell']

    total_buy_val = sum(row['total_val'] for row in buy_data)
    total_sell_val = sum(row['total_val'] for row in sell_data)
    total_net_val = total_buy_val - total_sell_val

    print(f"--- ANALISA OPER-OPERAN LANJUTAN: {stock_code} ({period_start} - {period_end}) ---")
    print(f"Total Buy Value: {total_buy_val/1e9:.2f}B")
    print(f"Total Sell Value: {total_sell_val/1e9:.2f}B")
    print(f"Total Net Value (Buy-Sell): {total_net_val/1e9:.2f}B")
    print(f"Total Volume (Buy+Sell): {(total_buy_val + total_sell_val)/1e9:.2f}B")
    print("-" * 40)

    print("TOP BUYERS:")
    for row in sorted(buy_data, key=lambda x: x['total_val'], reverse=True)[:5]:
        broker_name = BROKER_MAPPING.get(row['broker_code'], 'UNKNOWN')
        broker_cat = BROKER_CATEGORY.get(broker_name, 'UNKNOWN')
        avg_price_str = f"{row['avg_price']:.2f}" if row['avg_price'] is not None else "N/A"
        print(f"  {row['broker_code']} ({broker_name}, {broker_cat}) | Value: {row['total_val']/1e9:.2f}B | Avg: {avg_price_str}")

    print("\nTOP SELLERS:")
    for row in sorted(sell_data, key=lambda x: x['total_val'], reverse=True)[:5]:
        broker_name = BROKER_MAPPING.get(row['broker_code'], 'UNKNOWN')
        broker_cat = BROKER_CATEGORY.get(broker_name, 'UNKNOWN')
        avg_price_str = f"{row['avg_price']:.2f}" if row['avg_price'] is not None else "N/A"
        print(f"  {row['broker_code']} ({broker_name}, {broker_cat}) | Value: {row['total_val']/1e9:.2f}B | Avg: {avg_price_str}")

    # Analisis Pola
    print("\n--- ANALISIS POLA ---")
    if total_buy_val + total_sell_val > 0 and abs(total_net_val) < 0.1 * (total_buy_val + total_sell_val): # Net value < 10% total volume
        print("Pola 1: Net flow relatif kecil dibandingkan total volume. Indikasi oper-operan / churning.")
    else:
        print("Pola 1: Net flow signifikan. Bukan oper-operan murni, tapi lebih ke akumulasi/distribusi bersih.")

    # Cek Average Price Spread
    top_buy_avg = None
    if buy_data:
        # Filter out None avg_price before sorting and accessing
        valid_buy_data = [d for d in buy_data if d['avg_price'] is not None]
        if valid_buy_data:
            top_buy_avg = sorted(valid_buy_data, key=lambda x: x['total_val'], reverse=True)[0]['avg_price']
    
    top_sell_avg = None
    if sell_data:
        # Filter out None avg_price
        valid_sell_data = [d for d in sell_data if d['avg_price'] is not None]
        if valid_sell_data:
            top_sell_avg = sorted(valid_sell_data, key=lambda x: x['total_val'], reverse=True)[0]['avg_price']

    if top_buy_avg is not None and top_sell_avg is not None:
        if top_sell_avg > top_buy_avg:
            print(f"Pola 2: Average Sell Price ({top_sell_avg:.2f}) > Average Buy Price ({top_buy_avg:.2f}). Ini sinyal bandar jual di atas harga beli.")
        elif top_buy_avg > top_sell_avg:
            print(f"Pola 2: Average Buy Price ({top_buy_avg:.2f}) > Average Sell Price ({top_sell_avg:.2f}). Ini sinyal bandar beli di atas harga jual (kurang menarik).")
        else:
            print("Pola 2: Tidak ada kesenjangan harga yang jelas antara top buyer dan top seller.")
    else:
        print("Pola 2: Tidak cukup data avg_price untuk analisis kesenjangan harga.")

    # Cek kategori broker (simple check, could be more advanced)
    top_buyer_broker_code = None
    top_seller_broker_code = None
    
    if buy_data:
        top_buyer_broker_code = sorted(buy_data, key=lambda x: x['total_val'], reverse=True)[0]['broker_code']
    if sell_data:
        top_seller_broker_code = sorted(sell_data, key=lambda x: x['total_val'], reverse=True)[0]['broker_code']

    if top_buyer_broker_code and top_seller_broker_code:
        top_buyer_name = BROKER_MAPPING.get(top_buyer_broker_code, 'UNKNOWN')
        top_seller_name = BROKER_MAPPING.get(top_seller_broker_code, 'UNKNOWN')
        top_buyer_cat = BROKER_CATEGORY.get(top_buyer_name, 'UNKNOWN')
        top_seller_cat = BROKER_CATEGORY.get(top_seller_name, 'UNKNOWN')

        if top_buyer_cat != 'UNKNOWN' and top_seller_cat != 'UNKNOWN' and top_buyer_cat == top_seller_cat:
            print(f"Pola 3: Top Buyer ({top_buyer_name}, {top_buyer_cat}) dan Top Seller ({top_seller_name}, {top_seller_cat}) berasal dari kategori yang sama. Indikasi oper-operan dalam satu grup.")
        else:
            print(f"Pola 3: Top Buyer ({top_buyer_name}, {top_buyer_cat}) dan Top Seller ({top_seller_name}, {top_seller_cat}) berasal dari kategori berbeda. Bukan oper-operan dalam satu grup.")
    else:
        print("Pola 3: Tidak cukup data untuk analisis kategori broker.")

if __name__ == "__main__":
    detect_churning_advanced(sys.argv[1], sys.argv[2], sys.argv[3])
