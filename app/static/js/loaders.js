// ─── Data Loaders & UI Actions ───
// Depends on: state.js (refs), charts.js (renderMrCharts, buildMrStockTable)

async function loadMarketReports() {
  mrReportsLoading.value = true;
  try {
    const res = await fetch('/api/market-reports?limit=500');
    const json = await res.json();
    const full = (json.data || []).filter(r => r.type === 'full' || r.type === 'akhir_sesi' || r.type === 'sesi1');
    if (mrFilter.value !== 'all') {
      mrReports.value = full.filter(r => r.type === mrFilter.value);
    } else {
      mrReports.value = full;
    }

    if (full.length) {
      const firstMonth = full[0].date.substring(0, 7);
      mrExpandedMonths.value[firstMonth] = true;
    }

    const dataForStats = mrFilter.value !== 'all' ? mrReports.value : full;
    const ihsgVals = dataForStats.map(r => r.ihsg_change).filter(v => v !== null);
    const avgIHSG = ihsgVals.length ? (ihsgVals.reduce((a,b) => a+b, 0) / ihsgVals.length) : 0;
    const allForeignStocks = new Set();
    dataForStats.forEach(r => (r.foreign_buy || []).forEach(s => allForeignStocks.add(s.stock)));
    const redDays = ihsgVals.filter(v => v < 0).length;
    mrStats.value = { totalReports: dataForStats.length, avgIHSG: Math.round(avgIHSG * 10) / 10, foreignStocks: allForeignStocks.size, redDays };

    mrForeignStocks.value = buildMrStockTable('foreign_buy', '#7C3AED');
    mrLocalStocks.value = buildMrStockTable('local_buy', '#06D9FF');

    setTimeout(() => renderMrCharts(full), 100);
  } catch(e) {
    console.error('Market report load failed:', e);
  }
  mrReportsLoading.value = false;
}

async function loadMrAnalysis() {
  mrLoadingAnalysis.value = true;
  try {
    const res = await fetch('/api/market-report-analysis');
    const json = await res.json();
    if (json.status === 'ok' && json.analysis) {
      mrAnalysis.value = json.analysis;
    }
  } catch(e) {
    console.error('Analysis load failed:', e);
  }
  mrLoadingAnalysis.value = false;
}

async function loadForeignOverview() {
  try {
    const res = await fetch('/api/market-reports?limit=5');
    const json = await res.json();
    const reports = json.data || [];
    if (!reports.length) return;
    const latest = reports[0];
    const fb = latest.foreign_buy || [];
    const lb = latest.local_buy || [];
    const map = {};
    fb.forEach(s => { map[s.stock] = { stock: s.stock, foreignBuy: s.value, localBuy: 0 }; });
    lb.forEach(s => {
      if (map[s.stock]) map[s.stock].localBuy = s.value;
      else map[s.stock] = { stock: s.stock, foreignBuy: 0, localBuy: s.value };
    });
    const stocks = Object.values(map).map(s => ({ ...s, net: s.foreignBuy - s.localBuy }));
    foreignOverviewStocks.value = stocks.filter(s => s.net > 0).sort((a, b) => b.net - a.net).slice(0, 10);
    pahlawanBursaStocks.value = stocks.filter(s => s.net < 0).sort((a, b) => (b.localBuy - b.foreignBuy) - (a.localBuy - a.foreignBuy)).slice(0, 10);
    dailyNetTotal.value = stocks.reduce((sum, s) => sum + s.net, 0);
    foreignStockCount.value = stocks.filter(s => s.net > 0).length;
    foreignActivitySummary.value = {
      totalForeign: fb.reduce((a, s) => a + s.value, 0),
      totalLocal: lb.reduce((a, s) => a + s.value, 0),
      date: latest.date,
    };
  } catch(e) {
    console.error('Foreign overview load failed:', e);
  }
}

async function loadBacktest() {
  mrBtLoading.value = true;
  mrBtError.value = null;
  try {
    const res = await fetch('/api/market-backtest');
    const json = await res.json();
    if (json.status === 'ok') {
      mrBtData.value = json;
    } else {
      mrBtError.value = 'Gagal muat data backtest';
    }
  } catch(e) {
    console.error('Backtest load failed:', e);
    mrBtError.value = 'Backtest error: ' + e.message;
  }
  mrBtLoading.value = false;
}

async function loadStocks() {
  try {
    const res = await fetch('/api/stocks');
    const data = await res.json();
    allStocks.value = (data.stocks || []).map(s => ({
      code: s.code, name: s.name || '',
      chg: 0, price: '-', sector: 'Other', score: 0,
    }));
  } catch(e) { console.error('Stocks load failed:', e); }
}

async function loadWatchlistData() {
  try {
    const res = await fetch('/api/watchlist/1');
    const data = await res.json();
    watchlist.value = (data.watchlist || []).map(w => ({ code: w.stock_code || w.code || '', chg: 0 }));
    watchlist.value.forEach(w => {
      fetch('/api/stock/' + w.code).then(r => r.json()).then(d => {
        w.chg = d.change_pct || 0;
      }).catch(() => {});
    });
  } catch(e) { console.error('Watchlist load failed:', e); }
}

// ── UI Actions ──

function switchMrTab(tab) {
  currentTab.value = tab;
  if (tab === 'overview') setTimeout(() => renderMrCharts(mrReports.value), 100);
  if (tab === 'analysis' && !mrAnalysis.value) loadMrAnalysis();
  if (tab === 'backtest' && !mrBtData.value) loadBacktest();
}

function setMrFilter(filter) {
  mrFilter.value = filter;
  loadMarketReports();
}

function switchView(view, tab) {
  currentView.value = view;
  if (view === 'marketreports') loadMarketReports();
  _viewChanging = true;
  currentTab.value = tab || 'overview';
  if (window.innerWidth <= 768) sidebarOpen.value = false;
}

function switchTheme(theme) {
  currentTheme.value = theme;
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value;
}

function closeSearch(e) {
  if (e.target === e.currentTarget) searchOpen.value = false;
}

function onSearchInput() {
  if (searchQuery.value) searchOpen.value = true;
}
