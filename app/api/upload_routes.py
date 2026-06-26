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
        
        conn = get_mysql_conn()
        cur = conn.cursor()
        
        cur.execute('DELETE FROM broker_summary WHERE stock_code = %s', (ticker,))
        
        sql = """INSERT INTO broker_summary 
                 (stock_code, broker_code, side, lots, value, avg_price) 
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        
        # side can be inferred if not present, default to BUY
        vals = [
            (ticker, b['broker_code'], b.get('side', 'BUY'), b['lots'], b['value'], b['avg_price']) 
            for b in buyers
        ]
        
        cur.executemany(sql, vals)
        conn.commit()
        conn.close()
        
        return {"status": "success", "imported": len(buyers), "ticker": ticker}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
