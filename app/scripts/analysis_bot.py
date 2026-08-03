import sqlite3, json, sys, os, urllib.request
from datetime import datetime, timedelta

DB_PATH = r"D:\Latihan\Saham\analisa-saham\app\database\stock.db"
RECS_CACHE = os.path.join(os.path.dirname(__file__), "..", "cache", "last_recommendations.json")

def query_3mo_backtest(code):
    """Backtest 3 bulan dari API learning."""
    try:
        req = urllib.request.Request(
            f"http://localhost:8001/api/learning/backtest/{code}?strategy=swing&period=3mo",
            headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read())
            trades = d.get("trades", [])
            if trades:
                win = sum(1 for t in trades if t.get("profit_pct", 0) > 0)
                total = len(trades)
                winrate = round(win / total * 100, 1) if total else 0
                avg_return = round(sum(t.get("profit_pct", 0) for t in trades) / total, 1) if total else 0
                return {"winrate": winrate, "total_signals": total, "avg_return": avg_return}
    except:
        pass
    return {"winrate": 0, "total_signals": 0, "avg_return": 0}


def score_stock_light(code, change_pct, volume_mult, is_fby, is_loser):
    """Score 0-100 tanpa backtest API. Fast."""
    score = 50
    reasons = []

    if is_fby and change_pct > 0:
        score += 25
        reasons.append(f"Naik {change_pct:+.1f}% asing beli")

    if volume_mult and volume_mult >= 15:
        score -= 10
        reasons.append(f"Vol spike {volume_mult}x — kejar?")
    elif volume_mult and volume_mult >= 5:
        score += 10
        reasons.append(f"Vol spike {volume_mult}x")
    elif volume_mult and volume_mult >= 3:
        score += 5

    if is_loser:
        score -= 20
        reasons.append(f"Loser {change_pct:+.1f}%")

    score = max(0, min(100, score))

    if score >= 65:
        action = "BELI"
        risk = "RENDAH" if score >= 80 else "SEDANG"
    elif score >= 35:
        action = "TUNGGU"
        risk = "SEDANG" if score >= 50 else "TINGGI"
    else:
        action = "LEWATI"
        risk = "TINGGI"

    reason_str = " | ".join(reasons[:2]) if reasons else "-"
    return action, risk, score, reason_str


def analyze():
    conn = sqlite3.connect(DB_PATH)

    # Get latest sesi1 + all available data
    row = conn.execute("""
        SELECT date, type, ihsg_change, gainer, loser, foreign_buy, local_buy,
               foreign_buy_yesterday, volume_spike
        FROM market_reports
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()

    if not row:
        return "Tidak ada data."

    date, type_, ihsg, gainers, losers, fbuy, lbuy, fby, vol_spike = row

    gainers_list = json.loads(gainers) if gainers and gainers != 'null' else []
    losers_list = json.loads(losers) if losers and losers != 'null' else []
    fby_list = json.loads(fby) if fby and fby != 'null' else []
    vol_spike_list = json.loads(vol_spike) if vol_spike and vol_spike != 'null' else []
    fbuy_list = json.loads(fbuy) if fbuy and fbuy != 'null' else []
    lbuy_list = json.loads(lbuy) if lbuy and lbuy != 'null' else []

    loser_codes = {l['stock'] for l in losers_list}
    fby_codes = {s['stock'] for s in fby_list}
    vol_codes = {s['stock']: s.get('multiplier', 0) for s in vol_spike_list}
    gainer_changes = {g['stock']: g['change_pct'] for g in gainers_list}
    loser_changes = {l['stock']: l['change_pct'] for l in losers_list}
    fby_changes = {s['stock']: s['change_pct'] for s in fby_list}

    # All candidates — max 15 stocks
    candidates = set()
    for s in fby_list: candidates.add(s['stock'])
    for s in vol_spike_list: candidates.add(s['stock'])
    for s in gainers_list[:5]: candidates.add(s['stock'])
    for s in losers_list[:5]: candidates.add(s['stock'])
    # Filter: skip if winner/loser from 6-10 with very low score potential
    candidates = set(list(candidates)[:15])

    # Load prev recommendations for diff
    prev_recs = {}
    try:
        prev_recs = json.load(open(RECS_CACHE))
    except:
        pass

    # Score each — NO backtest API call (too slow), use data we have
    results = []
    for code in sorted(candidates):
        change_pct = fby_changes.get(code) or gainer_changes.get(code, loser_changes.get(code, 0))
        vol_mult = vol_codes.get(code, 0)
        is_fby = code in fby_codes
        is_loser = code in loser_codes
        action, risk, score, reason = score_stock_light(code, change_pct, vol_mult, is_fby, is_loser)

        # Diff from prev
        prev = prev_recs.get(code, {}).get("action", "")
        diff = "→"
        if prev and prev != action:
            diff = "↑" if action == "BELI" else "↓"

        results.append({
            "code": code, "action": action, "risk": risk,
            "score": score, "reason": reason, "diff": diff,
            "change_pct": change_pct,
        })

    # Sort: BELI first, by score desc
    sort_key = {"BELI": 0, "TUNGGU": 1, "LEWATI": 2}
    results.sort(key=lambda x: (sort_key.get(x["action"], 9), -x["score"]))

    # Generate output
    ihsg_str = f"{float(ihsg):+.2f}%" if ihsg else "—"
    lines = [f"📅 Laporan: {date}", f"📊 IHSG: {ihsg_str}", ""]

    # Summary
    buy_count = sum(1 for r in results if r["action"] == "BELI")
    wait_count = sum(1 for r in results if r["action"] == "TUNGGU")
    skip_count = sum(1 for r in results if r["action"] == "LEWATI")
    lines.append(f"🟢 BELI {buy_count}  🟡 TUNGGU {wait_count}  ⚫ LEWATI {skip_count}")
    lines.append("")

    for r in results:
        act_emoji = "🟢" if r["action"] == "BELI" else "🟡" if r["action"] == "TUNGGU" else "⚫"
        risk_emoji = "✅" if r["risk"] == "RENDAH" else "⚠️" if r["risk"] == "SEDANG" else "❌"
        change_str = f"{r['change_pct']:+.1f}%" if r['change_pct'] else ""
        lines.append(
            f"{act_emoji} {r['code']}: {r['action']} {r['diff']} | {risk_emoji} {r['risk']} | "
            f"Skor{r['score']} | {change_str}"
        )
        if r['reason'] and r['reason'] != '-':
            lines.append(f"   └ {r['reason']}")

    lines.append("")
    lines.append(f"✅ AI Rekomendasi — {datetime.now().strftime('%d %b %H:%M')}")

    # Save for next diff
    save_recs = {r["code"]: {"action": r["action"], "score": r["score"]} for r in results}
    json.dump(save_recs, open(RECS_CACHE, "w"))

    return "\n".join(lines)


if __name__ == '__main__':
    import urllib.request  # import here for inline use
    print(analyze())
