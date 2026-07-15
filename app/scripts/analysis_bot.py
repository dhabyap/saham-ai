import sqlite3, json, urllib.request, datetime, sys

DB_PATH = r"D:\Latihan\Saham\analisa-saham\app\database\stock.db"
API_URL = "http://localhost:20128/v1/chat/completions"
MODEL = "groq/llama-3.3-70b-versatile"

def query_stock_history(code, days=90):
    """Get historical price + volume data for backtest."""
    import urllib.request, json as j
    try:
        u = f"http://localhost:8001/api/learning/backtest/{code}?strategy=swing&period=3mo"
        req = urllib.request.Request(u, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = j.loads(r.read())
            trades = d.get("trades", [])
            if trades:
                win = sum(1 for t in trades if t.get("profit_pct", 0) > 0)
                total = len(trades)
                winrate = round(win / total * 100, 1) if total else 0
                avg_return = round(sum(t.get("profit_pct", 0) for t in trades) / total, 1) if total else 0
                return {"winrate": winrate, "total_signals": total, "avg_return": avg_return, "signals": trades[-5:]}
    except Exception as e:
        return {"error": str(e)[:100]}
    return {"error": "no data"}

def analyze():
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Get latest SESI 1 report only
    query = """
    SELECT date, type, ihsg_change, gainer, loser, foreign_buy, local_buy, 
           foreign_buy_yesterday, volume_spike, content
    FROM market_reports 
    WHERE type = 'sesi1'
    ORDER BY created_at DESC LIMIT 1
    """
    row = conn.execute(query).fetchone()
    
    if not row:
        # fallback: get any latest report
        row = conn.execute("""
            SELECT date, type, ihsg_change, gainer, loser, foreign_buy, local_buy, 
                   foreign_buy_yesterday, volume_spike, content
            FROM market_reports 
            ORDER BY created_at DESC LIMIT 1
        """).fetchone()
    
    conn.close()
    
    if not row:
        return "Tidak ada data market report."
    
    date, type_, ihsg, gainers, losers, foreign_buy, local_buy, fby, vol_spike, content = row
    
    # Parse JSON fields
    gainers_list = json.loads(gainers) if gainers and gainers != 'null' else []
    losers_list = json.loads(losers) if losers and losers != 'null' else []
    fby_list = json.loads(fby) if fby and fby != 'null' else []
    vol_spike_list = json.loads(vol_spike) if vol_spike and vol_spike != 'null' else []
    foreign_buy_list = json.loads(foreign_buy) if foreign_buy and foreign_buy != 'null' else []
    local_buy_list = json.loads(local_buy) if local_buy and local_buy != 'null' else []
    
    # 2. Collect candidate stocks from sesi1 data only
    candidates = set()
    for s in fby_list:
        candidates.add(s['stock'])
    for s in vol_spike_list:
        candidates.add(s['stock'])
    for s in gainers_list[:5]:
        candidates.add(s['stock'])
    
    # If no sesi1 candidates, use gainers from latest report
    if not candidates:
        for s in gainers_list[:5]:
            candidates.add(s['stock'])
        for s in foreign_buy_list[:3]:
            candidates.add(s['stock'])
    
    # 3. Get backtest data for each candidate
    backtest_data = {}
    for code in candidates:
        bt = query_stock_history(code)
        backtest_data[code] = bt
    
    # Build context — SESI 1 FOCUSED
    ctx_parts = [f"Market Report {date} ({type_})", f"IHSG Change: {ihsg}%"]
    
    if fby_list:
        ctx_parts.append("\n📈 Naik setelah asing beli kemarin (SESI 1):")
        for s in fby_list:
            ctx_parts.append(f"  {s['stock']}: +{s['change_pct']}% volume Rp{s.get('volume',0):,.0f}")
    
    if vol_spike_list:
        ctx_parts.append("\n📊 Lonjakan volume (SESI 1):")
        for s in vol_spike_list:
            ctx_parts.append(f"  {s['stock']}: {s['multiplier']}x volume normal")
    
    if gainers_list:
        ctx_parts.append("\nTop Gainer:")
        for g in gainers_list[:5]:
            ctx_parts.append(f"  {g['stock']}: +{g['change_pct']}%")
    
    if losers_list:
        ctx_parts.append("\nTop Loser:")
        for l in losers_list[:5]:
            ctx_parts.append(f"  {l['stock']}: {l['change_pct']}%")
    
    # Backtest data & recommendation generation
    ctx_parts.append("\n📊 HISTORICAL BACKTEST (3 bulan terakhir):")
    rec_lines = []
    for code in sorted(candidates):
        bt = backtest_data.get(code, {})
        if "winrate" in bt:
            win = bt["winrate"]
            avg = bt["avg_return"]
            # risk tier
            if win >= 70 and avg >= 5:
                risk = "Rendah"
                action = "BELI"
            elif win >= 40 and avg >= 0:
                risk = "Sedang"
                action = "TUNGGU"
            else:
                risk = "Tinggi"
                action = "JANGAN"
            ctx_parts.append(f"  {code}: winrate {win}%, avg return {avg}% ({bt['total_signals']} sinyal)")
            rec_lines.append(f"- {code}: {action} | {risk} | winrate {win}% avg {avg}%")
        elif "error" in bt:
            ctx_parts.append(f"  {code}: backtest error ({bt['error']})")
        else:
            ctx_parts.append(f"  {code}: no backtest data")
    # Append concise recommendation block for LLM
    if rec_lines:
        ctx_parts.append("\n🗒️ Rekomendasi Singkat (auto‑gen):")
        ctx_parts.extend(rec_lines)

    ctx = "\n".join(ctx_parts)
    
    prompt = f"""Anda analis saham IDX spesialis sesi 1. HANYA rekomendasi dari kandidat saham di bawah.

DATA SESI 1:
{ctx}

INSTRUKSI:
1. HANYA analisis saham yang tercantum di atas — JANGAN rekomendasi saham lain
2. Gunakan data backtest 3 bulan terakhir: winrate tinggi + avg return positif → prioritaskan BUY
3. Kandidat dari "Naik setelah asing beli kemarin" + "Lonjakan volume" adalah prioritas utama
4. Pertimbangkan IHSG trend, volume spike multiplier, dan backtest winrate
5. Output setiap baris format:
   - TICKER: BUY/WAIT/SELL | Risk Tinggi/Sedang/Rendah | Alasan singkat (sebut backtest winrate jika ada)

Contoh output:
- BREN: BELI | SEDANG | Naik 4.4% setelah asing beli. Backtest winrate 65% dalam 3 bulan
- PTPW: TUNGGU | TINGGI | Volume spike 11x tp perlu konfirmasi lanjut besok
"""
    
    p = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 1000}).encode()
    req = urllib.request.Request(API_URL, data=p,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode()
            # Parse streaming JSON response
            lines = raw.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("data: "):
                    line = line[6:]
                if not line:
                    continue
                try:
                    res = json.loads(line)["choices"][0]["message"]["content"]
                    break
                except (json.JSONDecodeError, KeyError):
                    continue
            else:
                # Try parsing as single JSON
                res = json.loads(lines[0])["choices"][0]["message"]["content"]
        
        # Save to DB
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO ai_recommendations (reasoning) VALUES (?)", (res,))
        conn.commit()
        conn.close()
        return res
    except Exception as e:
        return f"Error AI: {str(e)[:200]}"

if __name__ == '__main__':
    print(analyze())
