import sqlite3, json, urllib.request, datetime, sys

DB_PATH = r"D:\Latihan\Saham\analisa-saham\app\database\stock.db"
MODEL = "groq/llama-3.3-70b-versatile"

def analyze():
    conn = sqlite3.connect(DB_PATH)
    # Query: Get latest market report
    query = """
    SELECT date, type, ihsg_change, gainer, loser, foreign_buy, local_buy, content
    FROM market_reports 
    ORDER BY created_at DESC LIMIT 1
    """
    row = conn.execute(query).fetchone()
    conn.close()
    
    if not row: return "No market data available."
    
    # Parse JSON data
    date, type_, ihsg, gainers, losers, foreign_buy, local_buy, content = row
    
    # Build context
    ctx = f"""Market Report {date} ({type_})
IHSG Change: {ihsg}%
Top Gainers: {gainers}
Top Losers: {losers}
Foreign Buy: {foreign_buy}
Local Buy: {local_buy}
Summary: {content}
"""
    
    prompt = f"""You are an expert Indonesian Stock Analyst.
    Analyze this market report:
    {ctx}
    
    Based on this data:
    1. Identify 3-5 stocks with BUY/WAIT/SELL recommendation
    2. Focus on stocks with strong foreign buying or volume spikes
    3. Consider market sentiment (IHSG trend)
    4. Include risk level (High/Medium/Low)
    5. Keep it concise in Indonesian
    
    Format each line:
    - Ticker: Rating | Risk | Reason
    """
    
    p = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 800}).encode()
    req = urllib.request.Request("http://localhost:20128/v1/chat/completions", data=p,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.loads(r.read().decode().split("\n")[0])["choices"][0]["message"]["content"]
        
        # Save to DB
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO ai_recommendations (reasoning) VALUES (?)", (res,))
        conn.commit()
        conn.close()
        return res

if __name__ == '__main__':
    print(analyze())
