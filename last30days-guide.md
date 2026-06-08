# last30days Skill — Panduan Pakai

Skill research: tarik opini publik dari Reddit, X, YouTube, HN, Polymarket, GitHub, web — 30 hari terakhir.

## Cara Panggil

Di Hermes, tinggal ketik aja di chat:

```
last30days "saham BBCA 2025"
last30days "nvidia earnings reaction"
last30days "AI video tools sentiment"
```

Hermes bakal otomatis load skill + jalanin Python engine.

## Opsi Penting

| Opsi | Fungsi |
|------|--------|
| `--days=7` | Ubah lookback (default 30) |
| `--search=reddit,youtube` | Batasi sumber |
| `--deep` | Recall tinggi (lebih lambat) |
| `--quick` | Cepet (lower recall) |
| `--subreddits=SaaS,Entrepreneur` | Target subreddit tertentu |
| `--x-handle=elonmusk` | Target akun X spesifik |
| `--github-repo=owner/repo` | Aktivitas repo GitHub |
| `--competitors=3` | Auto-compare kompetitor |
| `--web-backend=brave` | Pake Brave Search (butuh API key) |

## Engine Langsung (via terminal)

Klo mau panggil langsung dari terminal (tanpa lewat chat Hermes):

```bash
cd "$HERMES_HOME/skills/research/last30days"
python3 scripts/last30days.py "saham perbankan Indonesia 2025" --days=7
```

## Sumber Gratis (No API Key)

- ✅ **Reddit** — diskusi publik
- ✅ **Hacker News** — tech discussion
- ✅ **Polymarket** — prediksi pasar
- ✅ **GitHub** — aktivitas repo

## Sumber Butuh Setup

| Sumber | Setup |
|--------|-------|
| **X/Twitter** | `--x-handle=` — butuh cookie AUTH_TOKEN/CT0 |
| **YouTube** | `brew install yt-dlp` atau `pip install yt-dlp` |
| **Web Search** | Set `BRAVE_API_KEY` di .env |
| **TikTok/IG** | ScrapeCreators API key |

## Contoh Spesifik Saham

```
last30days "saham BBCA" --subreddits=indonesia,finansial --days=7
last30days "prospek perbankan Indonesia 2025" --search=reddit
last30days "investasi saham 2025" --deep
```

## Output

Setelah jalan, skill ngasih output format:

```
🌐 last30days v3.3.2 · synced 2026-06-08

What I learned:
...
KEY PATTERNS from the research:
1. ...
✅ All agents reported back!
```

File raw research disave ke `~/Documents/Last30Days/` (bs diubah via env `LAST30DAYS_MEMORY_DIR`).

## Cek Status

```bash
cd "$HERMES_HOME/skills/research/last30days"
python3 scripts/last30days.py --diagnose
```

Nunjukin sumber mana yg available + butuh API key apa.