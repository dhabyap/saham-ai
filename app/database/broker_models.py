"""Broker tracking models — identify foreign vs domestic broker activity"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
from typing import Optional
from app.database.database import get_db, DB_TYPE


KNOWN_FOREIGN_BROKERS = {
    "CGS-CIMB": "CGS-CIMB Sekuritas",
    "CREDIT SUISSE": "Credit Suisse Sekuritas",
    "DBS": "DBS Vickers Sekuritas",
    "GOLDMAN": "Goldman Sachs",
    "HSBC": "HSBC Sekuritas",
    "JPMORGAN": "JP Morgan Sekuritas",
    "MORGAN": "Morgan Stanley",
    "MACQUARIE": "Macquarie Sekuritas",
    "NOMURA": "Nomura Sekuritas",
    "UBS": "UBS Sekuritas",
    "BNP": "BNP Paribas",
    "DEUTSCHE": "Deutsche Bank",
    "CITI": "Citigroup Sekuritas",
    "CLSA": "CLSA Sekuritas",
    "KEPPEL": "Keppel Sekuritas",
    "MIRAE": "Mirae Asset Sekuritas",
    "SAMSUNG": "Samsung Sekuritas",
    "DAEWOO": "Daewoo Sekuritas",
    "YUANTA": "Yuanta Sekuritas",
    "RHB": "RHB Sekuritas",
    "MAYBANK": "Maybank Sekuritas",
    "OCBC": "OCBC Sekuritas",
    "UOB": "UOB Kay Hian",
    "KIM": "Kim Eng Sekuritas",
    "TRIMEGAH": "Trimegah Sekuritas",
}

# IDX 2-letter broker codes → full name + is_foreign flag
# Sumber: kode anggota bursa BEI
BROKER_CODE_MAP = {
    "AG": ("Anugerah Sekuritas", False),
    "AI": ("AI Sekuritas", False),
    "AK": ("Ajaib Sekuritas", True),
    "AO": ("AO Sekuritas", False),
    "AP": ("Aspac Sekuritas", False),
    "AR": ("Artha Sekuritas", False),
    "AZ": ("Alfa Sekuritas", False),
    "BB": ("BCA Sekuritas", True),
    "BK": ("Barclays Capital", True),
    "BN": ("BNI Sekuritas", False),
    "BP": ("Bank Panin Sekuritas", False),
    "BR": ("BRI Danareksa", False),
    "BS": ("Binaartha Sekuritas", False),
    "CC": ("CLSA Sekuritas", True),
    "CG": ("CGS-CIMB Sekuritas", True),
    "CI": ("Citigroup Sekuritas", True),
    "CP": ("Ciptadana Sekuritas", False),
    "CS": ("Credit Suisse", True),
    "DB": ("Deutsche Bank", True),
    "DG": ("DWG Sekuritas", False),
    "DR": ("Danareksa Sekuritas", False),
    "DS": ("DBS Vickers", True),
    "DX": ("Dxchange Sekuritas", False),
    "ER": ("Erdikha Elit Sekuritas", False),
    "FB": ("Firman Bima Sekuritas", False),
    "FG": ("Fauzan Gani Sekuritas", False),
    "FP": ("Fortis Asia", False),
    "GR": ("Graham Reksa", False),
    "GS": ("Goldman Sachs", True),
    "HD": ("HD Capital", False),
    "HS": ("HSBC Sekuritas", True),
    "IF": ("Indo Premier Sekuritas", False),
    "IG": ("Indo Ganeca Sekuritas", False),
    "IP": ("Indopremier Sekuritas", False),
    "JD": ("JD Bower", False),
    "JP": ("JP Morgan", True),
    "KG": ("KGI Sekuritas", False),
    "KI": ("Kim Eng Sekuritas", True),
    "KP": ("Kresna Graha Sekuritas", False),
    "KZ": ("Macquarie Sekuritas", True),
    "MA": ("Mandiri Sekuritas", False),
    "MB": ("Maybank Sekuritas", True),
    "MC": ("Macquarie Sekuritas", True),
    "MG": ("Mega Capital", False),
    "MH": ("Mandiri Sekuritas", False),
    "MI": ("Mirae Asset", True),
    "MN": ("MNC Sekuritas", False),
    "MP": ("MNC Kapital", False),
    "MR": ("Merrill Lynch", True),
    "MS": ("Morgan Stanley", True),
    "NC": ("NC Sekuritas", False),
    "NH": ("NH Korindo", False),
    "NM": ("Nomura Sekuritas", True),
    "NS": ("Nusantara Sekuritas", False),
    "OC": ("OCBC Sekuritas", True),
    "OD": ("Oscar Dharma", False),
    "OK": ("Oto Kredit", False),
    "OP": ("Optima Kharya", False),
    "OS": ("OSK Nusadana", False),
    "PD": ("Mandiri Sekuritas", False),
    "PG": ("Panin Sekuritas", False),
    "PH": ("Phillip Sekuritas", True),
    "RB": ("Royal Bank", True),
    "RG": ("RHB OSK", True),
    "RX": ("RHB Sekuritas Indonesia", True),
    "SA": ("Samuel Sekuritas", False),
    "SB": ("Sinarmas Sekuritas", False),
    "SG": ("Sugeng Santoso", False),
    "SM": ("Semesta Indovest", False),
    "SQ": ("Sucor Sekuritas", False),
    "ST": ("Standard Chartered", True),
    "TP": ("Trimegah Sekuritas", False),
    "UA": ("UAB Sekuritas", False),
    "UB": ("UOB Kay Hian", True),
    "UF": ("UFO Sekuritas", False),
    "UO": ("UOB Kay Hian", True),
    "VP": ("Valbury Sekuritas", False),
    "XA": ("XAsia Sekuritas", False),
    "XC": ("Xcelencia", False),
    "XL": ("XL Sekuritas", False),
    "YA": ("Yuanta Sekuritas", True),
    "YJ": ("Yujin Sekuritas", False),
    "YP": ("YP Sekuritas", False),
    "YU": ("Citigroup Sekuritas", True),
    "ZP": ("ZPA Sekuritas", False),
}


# Broker classification for AI recommendation signals
# Based on: https://www.idx.co.id/id/anggota-bursa-dan-partisipan/daftar-anggota-bursa
# Categories:
#   smart_money  → foreign brokers + global investment banks
#   institutional → domestic institutional brokers (bank securities, big local)
#   retail       → domestic retail brokers (individual investors)
BROKER_CLASSIFICATION = {
    # === SMART MONEY (Foreign / Global) ===
    "BB": "smart_money",  # BCA Sekuritas (JV foreign)
    "BK": "smart_money",  # Barclays Capital
    "CC": "smart_money",  # CLSA Sekuritas
    "CG": "smart_money",  # CGS-CIMB Sekuritas
    "CI": "smart_money",  # Citigroup Sekuritas
    "CS": "smart_money",  # Credit Suisse
    "DB": "smart_money",  # Deutsche Bank
    "DS": "smart_money",  # DBS Vickers
    "GS": "smart_money",  # Goldman Sachs
    "HS": "smart_money",  # HSBC Sekuritas
    "JP": "smart_money",  # JP Morgan
    "KI": "smart_money",  # Kim Eng Sekuritas
    "KZ": "smart_money",  # Macquarie Sekuritas
    "MB": "smart_money",  # Maybank Sekuritas
    "MC": "smart_money",  # Macquarie Sekuritas
    "MI": "smart_money",  # Mirae Asset
    "MR": "smart_money",  # Merrill Lynch
    "MS": "smart_money",  # Morgan Stanley
    "NM": "smart_money",  # Nomura Sekuritas
    "OC": "smart_money",  # OCBC Sekuritas
    "PH": "smart_money",  # Phillip Sekuritas
    "RB": "smart_money",  # Royal Bank
    "RG": "smart_money",  # RHB OSK
    "RX": "smart_money",  # RHB Sekuritas Indonesia
    "ST": "smart_money",  # Standard Chartered
    "UB": "smart_money",  # UOB Kay Hian
    "UO": "smart_money",  # UOB Kay Hian
    "YA": "smart_money",  # Yuanta Sekuritas
    "YU": "smart_money",  # Citigroup Sekuritas

    # === INSTITUSIONAL LOKAL ===
    "BN": "institutional",  # BNI Sekuritas
    "BR": "institutional",  # BRI Danareksa
    "DR": "institutional",  # Danareksa Sekuritas
    "IF": "institutional",  # Indo Premier Sekuritas
    "IP": "institutional",  # Indopremier Sekuritas
    "MA": "institutional",  # Mandiri Sekuritas
    "MH": "institutional",  # Mandiri Sekuritas
    "NH": "institutional",  # NH Korindo
    "SA": "institutional",  # Samuel Sekuritas
    "TP": "institutional",  # Trimegah Sekuritas

    # === RETAIL ===
    "AG": "retail",  # Anugerah Sekuritas
    "AK": "smart_money",  # Ajaib Sekuritas (asing)
    "AP": "retail",  # Aspac Sekuritas
    "AR": "retail",  # Artha Sekuritas
    "AT": "retail",  # (unknown retail)
    "AZ": "retail",  # Alfa Sekuritas
    "BQ": "retail",  # (unknown retail)
    "BS": "retail",  # Binaartha Sekuritas
    "CD": "retail",  # (unknown retail)
    "CP": "retail",  # Ciptadana Sekuritas
    "DH": "retail",  # (unknown retail)
    "DP": "retail",  # (unknown retail)
    "DU": "retail",  # (unknown retail)
    "DX": "retail",  # Dxchange Sekuritas
    "EP": "retail",  # (unknown retail)
    "ER": "retail",  # Erdikha Elit Sekuritas
    "ES": "retail",  # (unknown retail)
    "FB": "retail",  # Firman Bima Sekuritas
    "FG": "retail",  # Fauzan Gani Sekuritas
    "FO": "retail",  # (unknown retail)
    "FP": "retail",  # Fortis Asia
    "FS": "retail",  # (unknown retail)
    "FZ": "retail",  # (unknown retail)
    "GI": "retail",  # (unknown retail)
    "GR": "retail",  # Graham Reksa
    "HD": "retail",  # HD Capital
    "HP": "retail",  # (unknown retail)
    "ID": "retail",  # (unknown retail)
    "IG": "retail",  # Indo Ganeca Sekuritas
    "IU": "retail",  # (unknown retail)
    "JD": "retail",  # JD Bower
    "KG": "retail",  # KGI Sekuritas
    "KK": "retail",  # (unknown retail)
    "KP": "retail",  # Kresna Graha Sekuritas
    "LG": "retail",  # (unknown retail)
    "LS": "retail",  # (unknown retail)
    "MG": "retail",  # Mega Capital
    "MN": "retail",  # MNC Sekuritas
    "MP": "retail",  # MNC Kapital
    "NC": "retail",  # NC Sekuritas
    "NI": "retail",  # (unknown retail)
    "NS": "retail",  # Nusantara Sekuritas
    "OD": "retail",  # Oscar Dharma
    "OK": "retail",  # Oto Kredit
    "OP": "retail",  # Optima Kharya
    "OS": "retail",  # OSK Nusadana
    "PC": "retail",  # (unknown retail)
    "PD": "retail",  # Mandiri Sekuritas (retail desk)
    "PF": "retail",  # (unknown retail)
    "PG": "retail",  # Panin Sekuritas
    "PP": "retail",  # (unknown retail)
    "QA": "retail",  # (unknown retail)
    "RF": "retail",  # (unknown retail)
    "RO": "retail",  # (unknown retail)
    "RS": "retail",  # (unknown retail)
    "SB": "retail",  # Sinarmas Sekuritas
    "SF": "retail",  # (unknown retail)
    "SG": "retail",  # Sugeng Santoso
    "SH": "retail",  # (unknown retail)
    "SM": "retail",  # Semesta Indovest
    "SQ": "retail",  # Sucor Sekuritas
    "SS": "retail",  # (unknown retail)
    "TF": "retail",  # (unknown retail)
    "TS": "retail",  # (unknown retail)
    "UF": "retail",  # UFO Sekuritas
    "VP": "retail",  # Valbury Sekuritas
    "XA": "retail",  # XAsia Sekuritas
    "XC": "retail",  # Xcelencia
    "XL": "retail",  # XL Sekuritas
    "YB": "retail",  # (unknown retail)
    "YJ": "retail",  # Yujin Sekuritas
    "YO": "retail",  # (unknown retail)
    "YP": "retail",  # YP Sekuritas
    "ZP": "retail",  # ZPA Sekuritas
    "ZR": "retail",  # (unknown retail)
}


def get_broker_category(broker_code: str) -> str:
    """Get broker classification: smart_money, institutional, retail, or unknown.
    
    Priority:
    1. Explicit BROKER_CLASSIFICATION override
    2. is_foreign flag from BROKER_CODE_MAP:
       - foreign (True) → smart_money (never retail)
       - domestic (False) → retail
    3. Not in CODE_MAP → unknown
    """
    code = broker_code.strip().upper()
    # Explicit override first
    if code in BROKER_CLASSIFICATION:
        return BROKER_CLASSIFICATION[code]
    # Fall back to is_foreign flag
    entry = BROKER_CODE_MAP.get(code)
    if entry:
        _, is_foreign = entry
        return "smart_money" if is_foreign else "retail"
    return "unknown"


def get_broker_category_label(category: str) -> tuple:
    """Return (label, icon, color) for a broker category."""
    labels = {
        "smart_money": ("Smart Money", "🌍", "#2563eb"),
        "institutional": ("Institusi", "🏦", "#7c3aed"),
        "retail": ("Retail", "👤", "#10b981"),
        "unknown": ("Unknown", "❓", "#6b7280"),
    }
    return labels.get(category, labels["unknown"])


def _sql():
    return """
    CREATE TABLE IF NOT EXISTS known_brokers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        broker_code TEXT UNIQUE NOT NULL,
        broker_name TEXT NOT NULL,
        is_foreign INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS broker_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,
        trade_date TEXT NOT NULL,
        broker_code TEXT NOT NULL,
        buy_volume INTEGER DEFAULT 0,
        sell_volume INTEGER DEFAULT 0,
        buy_value REAL DEFAULT 0,
        sell_value REAL DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        UNIQUE(stock_code, trade_date, broker_code)
    );
    """


def init_broker_db():
    """Create tables and seed known brokers."""
    with get_db() as conn:
        conn.executescript(_sql())
        _seed_brokers(conn)


def _seed_brokers(conn):
    """Insert known foreign brokers if not exist."""
    for code, name in KNOWN_FOREIGN_BROKERS.items():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO known_brokers (broker_code, broker_name, is_foreign) VALUES (?, ?, 1)",
                (code, name),
            )
        except Exception:
            pass
    # Also seed IDX 2-letter codes
    for code, (name, is_foreign) in BROKER_CODE_MAP.items():
        try:
            existing = conn.execute("SELECT id FROM known_brokers WHERE broker_code = ?", (code,)).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO known_brokers (broker_code, broker_name, is_foreign) VALUES (?, ?, ?)",
                    (code, name, 1 if is_foreign else 0),
                )
        except Exception:
            pass


def save_broker_transactions(stock_code: str, trade_date: str, transactions: list[dict]) -> int:
    """Save broker transactions. Returns count saved."""
    saved = 0
    with get_db() as conn:
        for t in transactions:
            try:
                conn.execute(
                    """INSERT OR REPLACE INTO broker_transactions
                       (stock_code, trade_date, broker_code, buy_volume, sell_volume, buy_value, sell_value)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        stock_code.upper(),
                        trade_date,
                        t.get("broker_code", "").upper(),
                        t.get("buy_volume", 0),
                        t.get("sell_volume", 0),
                        t.get("buy_value", 0),
                        t.get("sell_value", 0),
                    ),
                )
                saved += 1
            except Exception:
                continue
    return saved


def get_broker_transactions(stock_code: str, trade_date: str = None) -> list[dict]:
    """Get broker transactions for a stock, optionally filtered by date."""
    with get_db() as conn:
        if trade_date:
            cur = conn.execute(
                """SELECT bt.*, kb.is_foreign, kb.broker_name
                   FROM broker_transactions bt
                   LEFT JOIN known_brokers kb ON bt.broker_code = kb.broker_code
                   WHERE bt.stock_code = ? AND bt.trade_date = ?
                   ORDER BY (bt.buy_value + bt.sell_value) DESC""",
                (stock_code.upper(), trade_date),
            )
        else:
            cur = conn.execute(
                """SELECT bt.*, kb.is_foreign, kb.broker_name
                   FROM broker_transactions bt
                   LEFT JOIN known_brokers kb ON bt.broker_code = kb.broker_code
                   WHERE bt.stock_code = ?
                   ORDER BY bt.trade_date DESC, (bt.buy_value + bt.sell_value) DESC""",
                (stock_code.upper(),),
            )
        return [dict(r) for r in cur.fetchall()]


def calculate_broker_foreign_net(stock_code: str, trade_date: str) -> dict:
    """Calculate net foreign buy/sell from broker transactions."""
    rows = get_broker_transactions(stock_code, trade_date)
    if not rows:
        return {"foreign_buy": 0, "foreign_sell": 0, "foreign_net": 0, "domestic_buy": 0, "domestic_sell": 0, "total": 0}

    foreign_buy = sum(r.get("buy_value", 0) for r in rows if r.get("is_foreign"))
    foreign_sell = sum(r.get("sell_value", 0) for r in rows if r.get("is_foreign"))
    domestic_buy = sum(r.get("buy_value", 0) for r in rows if not r.get("is_foreign"))
    domestic_sell = sum(r.get("sell_value", 0) for r in rows if not r.get("is_foreign"))

    return {
        "foreign_buy": foreign_buy,
        "foreign_sell": foreign_sell,
        "foreign_net": foreign_buy - foreign_sell,
        "domestic_buy": domestic_buy,
        "domestic_sell": domestic_sell,
        "total": foreign_buy + foreign_sell + domestic_buy + domestic_sell,
    }


def get_broker_accumulation_summary(stock_code: str, days: int = 5) -> Optional[dict]:
    """Get multi-day foreign net trend from broker data."""
    with get_db() as conn:
        cur = conn.execute(
            """SELECT bt.trade_date,
                      SUM(CASE WHEN kb.is_foreign = 1 THEN bt.buy_value ELSE 0 END) as f_buy,
                      SUM(CASE WHEN kb.is_foreign = 1 THEN bt.sell_value ELSE 0 END) as f_sell,
                      SUM(CASE WHEN kb.is_foreign = 1 THEN bt.buy_value - bt.sell_value ELSE 0 END) as f_net
               FROM broker_transactions bt
               LEFT JOIN known_brokers kb ON bt.broker_code = kb.broker_code
               WHERE bt.stock_code = ?
               GROUP BY bt.trade_date
               ORDER BY bt.trade_date DESC
               LIMIT ?""",
            (stock_code.upper(), days),
        )
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return None

    total_net = sum(r["f_net"] for r in rows)
    accumulation_days = sum(1 for r in rows if r["f_net"] > 0)

    if accumulation_days >= days * 0.6:
        status = "accumulating"
    elif accumulation_days <= days * 0.3:
        status = "distributing"
    else:
        status = "neutral"

    return {
        "stock_code": stock_code.upper(),
        "days": len(rows),
        "total_net": total_net,
        "accumulation_days": accumulation_days,
        "distribution_days": len(rows) - accumulation_days,
        "status": status,
        "daily": rows,
    }


init_broker_db()
