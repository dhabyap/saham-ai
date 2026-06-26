import mysql.connector
from fastapi import APIRouter, HTTPException

router = APIRouter()

def get_mysql_conn():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='analisa_saham'
    )

@router.post("/api/broker/upload")
def upload_broker_data(data: dict):
    try:
        ticker = data.get('ticker')
        if not ticker:
            raise HTTPException(status_code=400, detail="Ticker missing")
            
        summary = data.get('broker_summary', {})
        buyers = summary.get('buyers', [])
        sellers = summary.get('sellers', [])
        
        conn = get_mysql_conn()
        cur = conn.cursor()
        
        cur.execute('DELETE FROM broker_summary WHERE stock_code = %s', (ticker,))
        
        from datetime import date
        today = date.today().isoformat()
        
        sql = """INSERT INTO broker_summary 
                 (stock_code, broker_code, side, lots, value, avg_price, period_from, period_to) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        
        vals = []
        for b in buyers:
            vals.append((ticker, b['broker_code'], 'buy', b['lots'], b['value'], b['avg_price'], today, today))
        for b in sellers:
            vals.append((ticker, b['broker_code'], 'sell', b['lots'], b['value'], b['avg_price'], today, today))
        
        if vals:
            cur.executemany(sql, vals)
        conn.commit()
        conn.close()
        
        return {"status": "success", "imported": len(vals), "ticker": ticker}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
