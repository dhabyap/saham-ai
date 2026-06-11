"""Service for parsing broker data and identifying foreign broker activity."""

import re
from datetime import datetime
from app.database.broker_models import (
    save_broker_transactions,
    calculate_broker_foreign_net,
    get_broker_transactions,
    get_broker_accumulation_summary,
    KNOWN_FOREIGN_BROKERS,
    BROKER_CODE_MAP,
)


def _get_foreign_flow_models():
    """Lazy import to avoid init_foreign_flow_db() crash on import."""
    from app.database.foreign_flow_models import save_foreign_flow, update_accumulation, init_foreign_flow_db
    init_foreign_flow_db()
    return save_foreign_flow, update_accumulation


def parse_broker_text(text: str, stock_code: str = "") -> list[dict]:
    """Parse raw broker text into structured transactions.
    
    Accepts formats:
    2026-06-06
    BROKER_CODE buy_vol sell_vol buy_val sell_val
    CGS-CIMB 1000 500 250000000 125000000
    
    Or: BROKER_CODE buy_val sell_val
    CGS-CIMB 250000000 125000000
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if not lines:
        return []

    # First line might be date
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", lines[0])
    if date_match:
        trade_date = date_match.group(1)
        data_lines = lines[1:]
    else:
        trade_date = datetime.now().strftime("%Y-%m-%d")
        data_lines = lines

    transactions = []
    for line in data_lines:
        parts = line.split()
        if len(parts) < 3:
            continue

        broker_code = parts[0].upper()

        # Heuristic: if we have 4-5 parts, format is: CODE buy_vol sell_vol buy_val sell_val
        # If 3 parts: CODE buy_val sell_val
        # If 2 parts: CODE net_value
        try:
            if len(parts) == 5:
                # BROKER buy_vol sell_vol buy_val sell_val
                buy_vol, sell_vol, buy_val, sell_val = map(_parse_num, parts[1:5])
            elif len(parts) == 4:
                # BROKER buy_val sell_val buy_vol (or buy_vol sell_vol buy_val)
                # Try to detect: if first two are huge (>10M), they're values
                v1, v2, v3 = _parse_num(parts[1]), _parse_num(parts[2]), _parse_num(parts[3])
                if v1 > 10000000 or v2 > 10000000:
                    buy_val, sell_val, buy_vol = v1, v2, int(v3)
                    sell_vol = 0
                else:
                    buy_vol, sell_vol, buy_val = int(v1), int(v2), v3
                    sell_val = 0
            elif len(parts) == 3:
                # BROKER buy_val sell_val
                buy_val, sell_val = map(_parse_num, parts[1:3])
                buy_vol = sell_vol = 0
            else:
                continue
        except (ValueError, IndexError):
            continue

        transactions.append({
            "broker_code": broker_code,
            "buy_volume": abs(int(buy_vol)) if isinstance(buy_vol, (int, float)) else 0,
            "sell_volume": abs(int(sell_vol)) if isinstance(sell_vol, (int, float)) else 0,
            "buy_value": abs(buy_val) if isinstance(buy_val, (int, float)) else 0,
            "sell_value": abs(sell_val) if isinstance(sell_val, (int, float)) else 0,
        })

    return transactions, trade_date


def _parse_num(s: str) -> float:
    """Parse number, removing commas."""
    s = s.replace(",", "").replace(".", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0


def save_and_analyze_broker_data(stock_code: str, raw_text: str) -> dict:
    """Parse, save, and return analysis of broker data."""
    transactions, trade_date = parse_broker_text(raw_text, stock_code)
    if not transactions:
        return {"error": "Tidak ada data broker valid. Format: BROKER_CODE buy_val sell_val"}

    saved = save_broker_transactions(stock_code, trade_date, transactions)
    if saved == 0:
        return {"error": "Gagal menyimpan data"}

    # Calculate foreign net
    stats = calculate_broker_foreign_net(stock_code, trade_date)

    # Sync to foreign_flow table so existing analysis works
    if stats["total"] > 0:
        try:
            save_ff, update_acc = _get_foreign_flow_models()
            save_ff([{
                "stock_code": stock_code,
                "trade_date": trade_date,
                "foreign_buy": stats["foreign_buy"],
                "foreign_sell": stats["foreign_sell"],
                "foreign_net": stats["foreign_net"],
                "domestic_buy": stats["domestic_buy"],
                "domestic_sell": stats["domestic_sell"],
                "total_volume": stats["total"],
                "source": "broker",
            }])
            update_acc(stock_code, trade_date)
        except Exception:
            pass

    # Build display
    rows = get_broker_transactions(stock_code, trade_date)
    detail_lines = []
    foreign_total = 0
    domestic_total = 0
    for r in rows:
        code = r['broker_code']
        # Cari nama broker dari IDX code map atau known_brokers di DB
        name = BROKER_CODE_MAP.get(code, (None, None))[0]
        if not name:
            name = r.get("broker_name", "") or KNOWN_FOREIGN_BROKERS.get(code, "")
        label = "🌍 ASING" if r.get("is_foreign") else "🏠 DOMESTIK"
        net_val = r.get("buy_value", 0) - r.get("sell_value", 0)
        sign = "+" if net_val > 0 else ""
        code_display = f"{code}" + (f" ({name})" if name else "")
        detail_lines.append(
            f"{label} {code_display}\n"
            f"  Buy Rp{r['buy_value']:,.0f} | Sell Rp{r['sell_value']:,.0f} | Net {sign}Rp{net_val:,.0f}"
        )
        if r.get("is_foreign"):
            foreign_total += net_val
        else:
            domestic_total += net_val

    f_sign = "+" if stats["foreign_net"] > 0 else ""
    d_sign = "+" if domestic_total > 0 else ""

    summary = (
        f"📊 *Data Broker {stock_code} ({trade_date})*\n"
        f"Tersimpan: {saved} broker\n\n"
        f"🌍 *Foreign Net:* {f_sign}Rp{stats['foreign_net']:,.0f}\n"
        f"  Buy: Rp{stats['foreign_buy']:,.0f}\n"
        f"  Sell: Rp{stats['foreign_sell']:,.0f}\n"
        f"🏠 *Domestik Net:* {d_sign}Rp{domestic_total:,.0f}\n\n"
        + "\n".join(detail_lines)
    )

    # Check accumulation trend
    acc = get_broker_accumulation_summary(stock_code, days=5)
    if acc and acc["days"] >= 2:
        if acc["status"] == "accumulating":
            summary += f"\n\n✅ *Akumulasi Asing {acc['accumulation_days']}/{acc['days']} hari* — Saham menarik"
        elif acc["status"] == "distributing":
            summary += f"\n\n⚠️ *Distribusi Asing {acc['distribution_days']}/{acc['days']} hari* — Waspada"
        summary += f"\nTotal Net 5 hari: Rp{acc['total_net']:,.0f}"

    return {
        "summary": summary,
        "stock_code": stock_code,
        "trade_date": trade_date,
        "saved": saved,
        "stats": stats,
    }


def format_broker_help() -> str:
    """Show help text for broker command."""
    known = "\n".join(f"  • {k} — {v}" for k, v in list(KNOWN_FOREIGN_BROKERS.items())[:15])
    return (
        "📋 *Cara Input Data Broker*\n\n"
        "Kirim: `/broker KODE_SAHAM\nYYYY-MM-DD\nBROKER buy_val sell_val`\n\n"
        "*Contoh:*\n"
        "```\n/broker BBCA\n2026-06-06\nCGS-CIMB 250000000 125000000\nMORGAN 180000000 90000000\nMANDIRI 50000000 200000000\nHSBC 300000000 100000000\n```\n\n"
        "*Format lain:*\n"
        "`BROKER buy_vol sell_vol buy_val sell_val` — 5 kolom\n"
        "`BROKER buy_val sell_val` — 3 kolom\n\n"
        "*Foreign Brokers dikenal:*\n"
        f"{known}\n  ...dan lainnya\n\n"
        "Data otomatis diidentifikasi asing/lokal & masuk ke analisa."
    )
