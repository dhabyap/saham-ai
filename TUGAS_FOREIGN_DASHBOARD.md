# Task: Make Foreign Flow the Default Dashboard View

## Problem
Dashboard default view shows generic Market Summary (FGI, advancing/declining). 
User wants the default to show **foreign accumulation data** — stocks where net foreign buy > 0, and flag "pahlawan bursa" (stocks where local buy dominates).

## User Investment Thesis
- Only trade stocks where foreign accumulation > local buying
- Net Foreign = foreign_total - local_total (per stock, from market_reports.json)
- Filter: only show stocks where net > 0 as recommendations
- "Pahlawan bursa" = stocks where local buy >> foreign buy — these are dangerous (retail hero stocks)
- Every foreign buy needs local context to be meaningful

## Data Source
- `market_reports.json` (served via `/api/market-reports`): each report has `date`, `foreign_buy` array `[{stock, value}]`, `local_buy` array `[{stock, value}]`
- Already computed in JS: `mrNetForeign` (computed ref, line 19-37) and `mrMonths` (line 38-59)
- Existing API: `/api/market-report-analysis` for aggregated analysis

## Files to Modify

### 1. app/templates/dashboard_vue.html
Modify the "Overview" tab (Dashboard view) to add:
- **Top section**: "🌍 Foreign Accumulation" — show top 10 stocks by net foreign (foreign_buy - local_buy)
- **Second section**: "⚠️ Pahlawan Bursa Warning" — show top stocks where local buy >> foreign buy
- **Net Foreign Summary card**: total net foreign flow (all stocks combined)
- **Foreign Activity Trend**: simple summary like "Asing beli bersih Rp X hari ini di Y saham"

Keep existing Market Summary cards but move them below the foreign data.

### 2. app/static/dashboard.js
Add data processing for foreign-focused overview:
- Add `async function loadForeignOverview()` that calls `/api/market-reports?limit=5` (just latest 5 days)
- Compute `netForeignStocks` sorted by net value descending
- Compute `pahlawanBursaStocks` sorted by local surplus (local - foreign) descending
- Compute `dailyNetTotal` = sum of all net foreign values for latest day
- Compute `foreignStockCount` = count of stocks with positive net foreign for latest day
- Store these in reactive refs: `foreignOverviewStocks`, `pahlawanBursaStocks`, `dailyNetTotal`, `foreignStockCount`
- Call `loadForeignOverview()` in `loadAllData()` alongside existing calls
- Expose new refs in return block

RESPONSE SHAPE from `/api/market-reports?limit=5`:
```json
{
  "status": "ok",
  "data": [
    {
      "date": "2026-06-05",
      "foreign_buy": [{"stock": "WIFI", "value": 21400000000}, ...],
      "local_buy": [{"stock": "TPIA", "value": 1140000000000}, ...]
    }
  ]
}
```

NET FOREIGN COMPUTATION (per stock, for latest report):
```
net = foreign_value - local_value
if net > 0 → foreign accumulating (good)
if net < 0 → local dominating (pahlawan bursa warning)
```

### 3. app/telegram/bot.py
Update `/help` command:
- Add section "*Foreign Flow:*" with `/marketreport` command info
- Update "/market - Overview market IDX" to mention foreign data
- Add note about investment thesis: "🔍 Cari saham dengan net foreign > 0 (asing akumulasi)"

## DESIGN RULES
1. Read TEMPLATE_OPENCODE.md in project root first and strictly follow it.
2. Keep all existing functionality — just ADD foreign data sections on top.
3. Dark theme styling: cards with purple (#7C3AED) accent for foreign, red (#EF5350) for pahlawan bursa warning.
4. Format values: rupiah in T/M format (Rp1.2T, Rp500M).
5. Net foreign card should be prominent, at the top of the Overview tab.

## VERIFICATION
1. Open `http://localhost:8001/` — Dashboard Overview tab shows "Foreign Accumulation" as first section
2. Shows top 10 stocks sorted by net foreign buy (descending)
3. Shows "Pahlawan Bursa" section with warning cards
4. Net foreign total card shows aggregate
5. Existing Market Summary cards still visible below
6. No JS errors in console
7. All formatting works for large rupiah values
