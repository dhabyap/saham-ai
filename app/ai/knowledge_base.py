from app.database import ai_crud


KNOWLEDGE_SEED = [
    {"category": "istilah_saham", "title": "Bullish",
     "content": "Kondisi pasar dimana harga cenderung naik. Ditandai dengan higher highs dan higher lows. Investor optimis terhadap pergerakan harga ke depan."},
    {"category": "istilah_saham", "title": "Bearish",
     "content": "Kondisi pasar dimana harga cenderung turun. Ditandai dengan lower highs dan lower lows. Investor pesimis terhadap pergerakan harga."},
    {"category": "istilah_saham", "title": "Sideways",
     "content": "Kondisi pasar dimana harga bergerak horizontal dalam range tertentu. Tidak ada tren yang jelas."},
    {"category": "istilah_saham", "title": "Support",
     "content": "Level harga dimana permintaan cukup kuat untuk mencegah harga turun lebih lanjut. Area yang cocok untuk entry buy."},
    {"category": "istilah_saham", "title": "Resistance",
     "content": "Level harga dimana supply cukup kuat untuk mencegah harga naik lebih lanjut. Area yang cocok untuk take profit."},
    {"category": "istilah_saham", "title": "Volume",
     "content": "Jumlah saham yang diperdagangkan dalam periode tertentu. Volume tinggi mengkonfirmasi kekuatan tren."},

    {"category": "candlestick", "title": "Doji",
     "content": "Pola candlestick dimana harga open dan close hampir sama. Menandakan keraguan pasar dan potensi reversal."},
    {"category": "candlestick", "title": "Hammer",
     "content": "Pola reversal bullish dengan body kecil dan shadow bawah panjang. Muncul setelah downtrend."},
    {"category": "candlestick", "title": "Engulfing",
     "content": "Pola reversal 2 candle. Bullish engulfing terjadi setelah downtrend, bearish engulfing setelah uptrend."},
    {"category": "candlestick", "title": "Morning Star",
     "content": "Pola reversal bullish 3 candle: candle panjang merah, doji, candle panjang hijau. Konfirmasi pembalikan tren."},
    {"category": "candlestick", "title": "Evening Star",
     "content": "Pola reversal bearish 3 candle: candle panjang hijau, doji, candle panjang merah. Tanda potensi puncak."},

    {"category": "fundamental", "title": "PER (Price to Earnings Ratio)",
     "content": "Rasio harga saham terhadap laba per saham. PER tinggi bisa berarti overvalued atau ekspektasi tinggi. PER rendah bisa berarti undervalued."},
    {"category": "fundamental", "title": "PBV (Price to Book Value)",
     "content": "Rasio harga saham terhadap nilai buku perusahaan. PBV < 1 bisa berarti undervalued."},
    {"category": "fundamental", "title": "Dividend Yield",
     "content": "Rasio dividen per saham dibagi harga saham. Semakin tinggi yield, semakin besar return dividen."},
    {"category": "fundamental", "title": "ROE (Return on Equity)",
     "content": "Rasio laba bersih terhadap ekuitas pemegang saham. ROE tinggi menandakan perusahaan efisien menghasilkan laba."},

    {"category": "technical", "title": "RSI (Relative Strength Index)",
     "content": "Oscillator yang mengukur kekuatan perubahan harga. RSI > 70 = overbought (potensi koreksi), RSI < 30 = oversold (potensi rebound)."},
    {"category": "technical", "title": "MACD (Moving Average Convergence Divergence)",
     "content": "Indikator momentum yang menunjukkan hubungan antara 2 MA. Golden Cross (MACD > Signal) = bullish, Death Cross = bearish."},
    {"category": "technical", "title": "Moving Average (MA)",
     "content": "Rata-rata harga dalam periode tertentu. MA20 untuk tren jangka pendek, MA50 untuk tren menengah."},
    {"category": "technical", "title": "Golden Cross",
     "content": "Sinyal bullish ketika MA jangka pendek (MA20) memotong di atas MA jangka panjang (MA50). Potensi tren naik."},
    {"category": "technical", "title": "Death Cross",
     "content": "Sinyal bearish ketika MA jangka pendek memotong di bawah MA jangka panjang. Potensi tren turun."},

    {"category": "strategi", "title": "Scalping",
     "content": "Strategi trading jangka sangat pendek (detik-menit). Target profit kecil 0.1-0.5%. Membutuhkan eksekusi cepat dan likuiditas tinggi."},
    {"category": "strategi", "title": "Swing Trading",
     "content": "Strategi trading jangka menengah (hari-minggu). Memanfaatkan swing harga. Target profit 5-15% per trade."},
    {"category": "strategi", "title": "Long Term Investing",
     "content": "Strategi investasi jangka panjang (bulan-tahun). Fokus pada fundamental perusahaan. Target pertumbuhan nilai dan dividen."},
    {"category": "strategi", "title": "Dividend Investing",
     "content": "Strategi memilih saham dengan dividen stabil dan tinggi. Fokus pada dividend yield dan konsistensi pembayaran dividen."},
]


def seed_knowledge_base():
    existing = ai_crud.search_knowledge("", limit=1)
    if existing:
        return
    for item in KNOWLEDGE_SEED:
        ai_crud.add_knowledge(
            category=item["category"],
            title=item["title"],
            content=item["content"],
            tags=[item["title"].lower().replace(" ", "_")],
            source="system_knowledge_base",
        )


def search_knowledge(query, category=None):
    return ai_crud.search_knowledge(query, category=category)


def get_knowledge_context(query, max_items=3):
    results = search_knowledge(query, max_items)
    if not results:
        return ""
    context = "\n".join(
        f"- {r['title']}: {r['content']}" for r in results
    )
    return f"\nKnowledge:\n{context}\n"


def get_knowledge_for_prompt(stock_data, strategy="swing"):
    context_parts = []
    rsi = stock_data.get("rsi", 0)
    macd = stock_data.get("macd_status", "")
    trend = stock_data.get("trend", "")

    if rsi:
        if rsi > 70:
            context_parts.append(search_knowledge("RSI overbought", "technical"))
        elif rsi < 30:
            context_parts.append(search_knowledge("RSI oversold", "technical"))

    if "golden" in macd.lower():
        context_parts.append(search_knowledge("Golden Cross", "technical"))
    elif "death" in macd.lower():
        context_parts.append(search_knowledge("Death Cross", "technical"))

    if strategy:
        context_parts.append(search_knowledge(strategy, "strategi"))

    flat = []
    for items in context_parts:
        for item in items[:2]:
            flat.append(f"- {item['title']}: {item['content']}")
    return "\n".join(flat[:5])
