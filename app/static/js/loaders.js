// ─── Data Loaders ───
// Memuat data dari API untuk semua view

// ── Client-Side Cache Layer ──
var _cache = {};

function getCached(url, ttlMs) {
  var entry = _cache[url];
  if (!entry) return null;
  if (Date.now() - entry.ts > ttlMs) { delete _cache[url]; return null; }
  return entry.data;
}

function setCache(url, data) {
  _cache[url] = { data: data, ts: Date.now() };
}

async function cachedFetch(url, ttlMs) {
  ttlMs = ttlMs || 5 * 60 * 1000;
  var cached = getCached(url, ttlMs);
  if (cached) return cached;
  var res = await fetch(url);
  var data = await res.json();
  setCache(url, data);
  return data;
}

// ── Cache Invalidation ──
function invalidateCache(pattern) {
  Object.keys(_cache).forEach(function(key) {
    if (key.includes(pattern)) delete _cache[key];
  });
}

function onCacheInvalidate(pattern) {
  if (typeof invalidateCache === 'function') {
    invalidateCache(pattern);
  }
  if (typeof _loadedViews !== 'undefined') {
    Object.keys(_loadedViews).forEach(function(key) {
      var view = pattern.replace('/api/', '');
      if (key.includes(view)) delete _loadedViews[key];
    });
  }
}

function clearAllCache() {
  if (typeof _cache !== 'undefined') {
    Object.keys(_cache).forEach(function(key) { delete _cache[key]; });
  }
  if (typeof _loadedViews !== 'undefined') {
    Object.keys(_loadedViews).forEach(function(key) { delete _loadedViews[key]; });
  }
}
// ─────────────────────────

// ── Dashboard ──
async function loadDashboardData() {
  overviewLoading.value = true;
  dashboardLoading.value = true;
  var results = await Promise.allSettled([
    fetch('/api/market-summary').then(function(r) { return r.json(); }),
    fetch('/api/top-gainers?limit=5').then(function(r) { return r.json(); }),
    fetch('/api/top-losers?limit=5').then(function(r) { return r.json(); }),
    fetch('/api/top-volume?limit=5').then(function(r) { return r.json(); }),
    fetch('/api/sector-performance').then(function(r) { return r.json(); }),
    fetch('/api/foreign-flow/summary').then(function(r) { return r.json(); }),
  ]);
  loadShareholders();
  loadWatchlistData();
  loadStocks();
  if (results[0].status === 'fulfilled' && results[0].value) applyMarketData(results[0].value);
  if (results[1].status === 'fulfilled' && results[1].value) applyGainersData(results[1].value);
  if (results[2].status === 'fulfilled' && results[2].value) applyLosersData(results[2].value);
  if (results[3].status === 'fulfilled' && results[3].value) applyVolumeData(results[3].value);
  if (results[4].status === 'fulfilled' && results[4].value) applySectorsData(results[4].value);
  if (results[5].status === 'fulfilled' && results[5].value) applyForeignData(results[5].value);
  overviewLoading.value = false;
  dashboardLoading.value = false;
  _loadedViews.dashboard = true;
}

// ── Day Trading ──
async function loadDayTradingView() {
  daytradingLoading.value = true;
  await Promise.allSettled([
    loadDayTradingData(),
    loadAnalysisHistory(),
  ]);
  daytradingLoading.value = false;
  _loadedViews.daytrading = true;
}

// ── Long Term ──
async function loadLongTermView() {
  longtermLoading.value = true;
  await Promise.allSettled([
    fetchWithTimeout('/api/long-term/candidates', 15000).then(function(json) {
      if (json && json.status === 'ok' && json.data && json.data.candidates) {
        applyLongtermData(json);
      }
    }),
    loadForeignFlowData(),
  ]);
  longtermLoading.value = false;
  _loadedViews.longterm = true;
}

// ── Analysis ──
async function loadAnalysisView() {
  analysisLoading.value = true;
  if (!allStocks.value.length) await loadStocks();
  await loadAnalysisHistory();
  analysisLoading.value = false;
  _loadedViews.analysis = true;
}

// ── Shareholders ──
async function loadShareholdersView() {
  shareholdersLoading.value = true;
  await loadShareholders();
  shareholdersLoading.value = false;
  _loadedViews.shareholders = true;
}

function applyMarketData(data) {
  market.value.fgi.value = data.fear_greed.index;
  market.value.fgi.label = data.fear_greed.label;
  market.value.advancing.count = data.advancing;
  market.value.advancing.change = data.advancing;
  market.value.advancing.pct = (data.advancing / data.total_stocks * 100).toFixed(0) + '%';
  market.value.declining.count = data.declining;
  market.value.declining.change = data.declining;
  market.value.declining.pct = (data.declining / data.total_stocks * 100).toFixed(0) + '%';
  market.value.avgChange = (data.avg_change >= 0 ? '+' : '') + data.avg_change.toFixed(2) + '%';
  market.value.totalVolume = formatVolume(data.total_volume);
  market.value.volumeChange = '';
  market.value.status = 'Open';
  market.value.hours = '09:00 - 15:00 WIB';
}

function applyGainersData(data) {
  var items = (data.gainers || []).map(function(item) {
    return { code: item.code, name: item.name, chg: (item.change_pct >= 0 ? '+' : '') + item.change_pct.toFixed(1) + '%' };
  });
  movers.value.gainers = items.slice(0, 5);
  allGainers.value = items;
}

function applyLosersData(data) {
  var items = (data.losers || []).map(function(item) {
    return { code: item.code, name: item.name, chg: (item.change_pct >= 0 ? '+' : '') + item.change_pct.toFixed(1) + '%' };
  });
  movers.value.losers = items.slice(0, 5);
  allLosers.value = items;
}

function applyVolumeData(data) {
  var items = (data.volumes || []).map(function(item) {
    return { code: item.code, name: item.name, vol: formatVolume(item.volume) };
  });
  movers.value.volume = items.slice(0, 5);
  allVolume.value = items;
}

function applySectorsData(data) {
  sectors.value = Object.entries(data).map(function(kv) {
    var name = kv[0], info = kv[1], perf = info.performance;
    var isPos = perf >= 0;
    var width = Math.min(Math.abs(perf) * 10, 100);
    var color = isPos ? 'var(--success)' : 'var(--danger)';
    var flowClass = info.flow === 'INFLOW' ? 'success' : info.flow === 'OUTFLOW' ? 'danger' : 'accent';
    return { name: name, width: width + '%', barColor: color, textColor: color, change: (isPos ? '+' : '') + perf.toFixed(2) + '%', flow: info.flow, flowClass: flowClass };
  });
}

function applyDaytradeData(data) {
  if (data.status === 'ok' && data.data && data.data.candidates && data.data.candidates.length > 0) {
    bpjsSignals.value = data.data.candidates.map(function(c) {
      return { code: c.code, signal: c.signal, signalClass: c.signal === 'ENTER' ? 'success' : c.signal === 'WAIT' ? 'warning' : 'danger', confidence: c.confidence, price: formatPrice(c.price) };
    });
  }
}

function applyLongtermData(data) {
  if (data.status === 'ok' && data.data && data.data.candidates && data.data.candidates.length > 0) {
    longTermSignals.value = data.data.candidates.map(function(c) {
      return { code: c.code, signal: c.signal, signalClass: c.signalClass || (c.signal === 'Active Accum' ? 'accent' : c.signal === 'Accum Watch' ? 'warning' : 'danger'), confidence: c.confidence, entryZone: c.entryZone };
    });
  }
}

function applyForeignData(data) {
  if (data.status === 'ok' && data.data) {
    var items = [];
    var accumulating = data.data.top_accumulating || [];
    var distributing = data.data.top_distributing || [];
    accumulating.forEach(function(item) {
      items.push({ code: item.stock_code || item.code, phase: 'Active Accum', signalClass: 'accent', confidence: item.confidence || 0, entryZone: item.entry_zone || 'N/A', accumDays: item.accumulation_days || item.accum_days || 0, rsStatus: item.strength || item.rs_status || 'Neutral' });
    });
    distributing.forEach(function(item) {
      items.push({ code: item.stock_code || item.code, phase: 'Distribution', signalClass: 'danger', confidence: item.confidence || 0, entryZone: 'N/A', accumDays: 0, rsStatus: 'Weak' });
    });
    if (items.length > 0) ltAccumulation.value = items;
  }
}

// ── Market Summary Load ──
async function loadMarketSummary() {
  try {
    var sum = await cachedFetch('/api/market-summary', 300000);
    var sent = await cachedFetch('/api/market-sentiment', 300000);
    var fg = sent.fear_greed || sum.fear_greed || { index: 50, label: 'Neutral' };
    var vol = sum.total_volume || 0;
    var volStr = vol >= 1e12 ? (vol/1e12).toFixed(1)+'T' : vol >= 1e9 ? (vol/1e9).toFixed(1)+'B' : vol >= 1e6 ? (vol/1e6).toFixed(1)+'M' : String(vol);
    market.value = {
      fgi: { value: fg.index || 50, label: fg.label || 'Neutral' },
      advancing: { count: sum.advancing || 0, change: '+0', pct: sum.total_stocks ? Math.round(sum.advancing/sum.total_stocks*100)+'%' : '0%' },
      declining: { count: sum.declining || 0, change: '0', pct: sum.total_stocks ? Math.round(sum.declining/sum.total_stocks*100)+'%' : '0%' },
      avgChange: (sum.avg_change != null ? (sum.avg_change >= 0 ? '+' : '') + sum.avg_change + '%' : '0%'),
      totalVolume: volStr, volumeChange: '-', status: 'Open', hours: '09:00 - 15:00 WIB',
    };
  } catch(e) { console.error('Market summary load failed:', e); }
}

async function loadTopMovers() {
  try {
    var g = await cachedFetch('/api/top-gainers?limit=10', 300000);
    var l = await cachedFetch('/api/top-losers?limit=10', 300000);
    var v = await cachedFetch('/api/top-volume?limit=10', 300000);
    var fmt = function(items) { return items.map(function(s) { return { code: s.code, name: s.name || s.stock_name || '', chg: (s.change_pct >= 0 ? '+' : '') + s.change_pct + '%', vol: s.volume ? (s.volume >= 1e9 ? (s.volume/1e9).toFixed(1)+'B' : (s.volume/1e6).toFixed(1)+'M') : '-' }; }); };
    movers.value = { gainers: fmt((g.gainers || []).slice(0,3)), losers: fmt((l.losers || []).slice(0,3)), volume: fmt((v.volumes || []).slice(0,3)) };
    allGainers.value = fmt(g.gainers || []);
    allLosers.value = fmt(l.losers || []);
    allVolume.value = fmt(v.volumes || []);
  } catch(e) { console.error('Top movers load failed:', e); }
}

async function loadSectors() {
  try {
    var data = await cachedFetch('/api/sector-performance', 600000);
    var maxPerf = Math.max.apply(null, Object.values(data).map(function(s) { return Math.abs(s.performance); }).concat([0.01]));
    sectors.value = Object.entries(data).map(function(kv) {
      var name = kv[0], s = kv[1], perf = s.performance;
      var width = Math.max(8, Math.min(100, (Math.abs(perf) / maxPerf) * 100));
      var isPos = perf >= 0;
      var barColor = isPos ? 'var(--success)' : 'var(--danger)';
      var fm = { INFLOW: { label: 'Inflow', cls: 'success' }, OUTFLOW: { label: 'Outflow', cls: 'danger' }, NEUTRAL: { label: 'Neutral', cls: 'accent' } };
      var f = fm[s.flow] || fm.NEUTRAL;
      return { name: name, width: width + '%', barColor: barColor, textColor: barColor, change: (perf >= 0 ? '+' : '') + perf.toFixed(2) + '%', flow: f.label, flowClass: f.cls };
    });
  } catch(e) { console.error('Sectors load failed:', e); }
}

async function loadStocks() {
  stocksLoading.value = true;
  try {
    var data = await cachedFetch('/api/stocks', 3600000);
    var SECTOR_GUESS = { BBCA:'Financials', BBRI:'Financials', BMRI:'Financials', BBNI:'Financials', TLKM:'Technology', EXCL:'Technology', TOWR:'Technology', ASII:'Consumer Cycl.', UNVR:'Consumer Cycl.', INDF:'Consumer Cycl.', ICBP:'Consumer Cycl.', HMSP:'Consumer Cycl.', GGRM:'Consumer Cycl.', ADRO:'Energy', ITMG:'Energy', PTBA:'Energy', MEDC:'Energy', CPIN:'Healthcare', KLBF:'Healthcare', JSMR:'Infrastructure', PGAS:'Infrastructure', SMGR:'Infrastructure', INTP:'Infrastructure', SMMA:'Infrastructure', AKRA:'Infrastructure', GOTO:'Technology' };
    allStocks.value = (data.stocks || []).map(function(s) { return { code: s.code, name: s.name || '', chg: 0, price: '-', sector: SECTOR_GUESS[s.code] || 'Other', score: 0 }; });
    analysisStocks.value = allStocks.value.slice();
    // Load scores
    allStocks.value.forEach(function(s, i) {
      fetch('/api/analyze/' + s.code).then(function(r) { return r.json(); }).then(function(d) {
        if (d.stock_code) {
          var chg = d.change_pct || 0; s.chg = chg;
          s.price = d.price ? 'Rp ' + Number(d.price).toLocaleString('id') : '-';
          s.score = d.confidence || 50;
          if (analysisStocks.value[i]) { analysisStocks.value[i] = Object.assign({}, analysisStocks.value[i], { chg: chg, price: s.price, score: s.score }); }
        }
      }).catch(function() {});
    });
  } catch(e) { console.error('Stocks load failed:', e); }
  stocksLoading.value = false;
}

// ── Shareholders ──
async function loadShareholders() {
  shareholdersLoading.value = true;
  shareholdersError.value = '';
  try {
    var data = await cachedFetch('/api/shareholders/periods', 3600000);
    if (data.status === 'ok') {
      shareholdersPeriods.value = data.periods || [];
      shareholdersLatestPeriod.value = data.latest || '';
      selectedPeriod.value = data.latest || '';
      shareholdersStats.value = data.stats || { total_records: 0, total_stocks: 0, total_holders: 0, top_holder: '-', period: 'all' };
      if (data.latest) {
        var topData = await cachedFetch('/api/shareholders/top?period=' + data.latest, 3600000);
        if (topData.status === 'ok') {
          topShareholders.value = topData.data || [];
          if (topShareholders.value.length) {
            shareholdersStats.value = Object.assign({}, shareholdersStats.value, { top_holder: topShareholders.value[0].shareholder_name });
          }
        }
        var stocksData = await cachedFetch('/api/shareholders/stocks?period=' + data.latest, 3600000);
        if (stocksData.status === 'ok') shStockList.value = stocksData.data || [];
        var popData = await cachedFetch('/api/shareholders/top?period=' + data.latest + '&min_pct=0.1&limit=30', 3600000);
        if (popData.status === 'ok') popularHolders.value = popData.data || [];
      } else {
        topShareholders.value = [];
        shStockList.value = [];
        popularHolders.value = [];
      }
    } else {
      shareholdersError.value = 'Gagal memuat ringkasan shareholder.';
    }
  } catch(e) {
    console.error('Shareholders load failed:', e);
    shareholdersError.value = 'Gagal mengambil data shareholder: ' + e.message;
  } finally {
    shareholdersLoading.value = false;
  }
  // Load enhanced chart data after basic data succeeds
  if (shareholdersStats.value.total_records > 0 && shareholdersLatestPeriod.value) {
    loadShareholdersEnhanced();
  }
}

async function loadShareholdersEnhanced() {
  shDistLoading.value = true;
  try {
    var period = shareholdersLatestPeriod.value;
    if (!period) { shDistLoading.value = false; return; }

    var results = await Promise.allSettled([
      fetch('/api/shareholders/distribution?period=' + period).then(function(r) { return r.json(); }),
      fetch('/api/shareholders/top-stocks?period=' + period + '&limit=10').then(function(r) { return r.json(); }),
      fetch('/api/shareholders/stats/detail?period=' + period).then(function(r) { return r.json(); }),
      fetch('/api/shareholders/concentration?period=' + period + '&threshold=5').then(function(r) { return r.json(); }),
      fetch('/api/shareholders/scatter-data?period=' + period).then(function(r) { return r.json(); }),
    ]);

    if (results[0].status === 'fulfilled' && results[0].value && results[0].value.status === 'ok')
      shDistribution.value = results[0].value.distribution;

    if (results[1].status === 'fulfilled' && results[1].value && results[1].value.status === 'ok')
      shTopStocks.value = results[1].value.data || [];

    if (results[2].status === 'fulfilled' && results[2].value && results[2].value.status === 'ok')
      shDetailStats.value = results[2].value.stats;

    if (results[3].status === 'fulfilled' && results[3].value && results[3].value.status === 'ok')
      shConcentration.value = results[3].value.dominant_stocks || [];

    if (results[4].status === 'fulfilled' && results[4].value && results[4].value.status === 'ok')
      shScatterData.value = results[4].value.data || [];

    window.Vue.nextTick(function() { renderShareholderChartsEnhanced(); });
  } catch(e) {
    console.error('Enhanced shareholders load failed:', e);
  } finally {
    shDistLoading.value = false;
  }
}

async function loadShareholdersByPeriod() {
  var period = selectedPeriod.value;
  if (!period) return;
  
  shareholdersLatestPeriod.value = period;
  shareholdersLoading.value = true;
  shareholdersError.value = '';
  
  try {
    var topData = await fetch('/api/shareholders/top?period=' + period).then(function(r) { return r.json(); });
    if (topData.status === 'ok') {
      topShareholders.value = topData.data || [];
      if (topShareholders.value.length) {
        shareholdersStats.value = Object.assign({}, shareholdersStats.value, { top_holder: topShareholders.value[0].shareholder_name });
      }
    }
    
    var stocksData = await fetch('/api/shareholders/stocks?period=' + period).then(function(r) { return r.json(); });
    if (stocksData.status === 'ok') shStockList.value = stocksData.data || [];
    
    var popData = await fetch('/api/shareholders/top?period=' + period + '&min_pct=0.1&limit=30').then(function(r) { return r.json(); });
    if (popData.status === 'ok') popularHolders.value = popData.data || [];
    
    loadShareholdersEnhanced();
  } catch(e) {
    console.error('Period reload failed:', e);
    shareholdersError.value = 'Gagal memuat data untuk periode ' + period;
  } finally {
    shareholdersLoading.value = false;
  }
}

function totalSharePct(rows) {
  return rows.reduce(function(sum, r) { return sum + (r.share_percent || 0); }, 0);
}
function dominantHolderPct(rows) {
  if (!rows.length) return '-';
  var top = rows.slice().sort(function(a,b) { return (b.share_percent||0) - (a.share_percent||0); })[0];
  return top.share_percent.toFixed(1) + '%';
}
async function searchStockShareholders() {
  var code = shStockQuery.value.trim().toUpperCase();
  if (!code) return;
  shStockLoading.value = true;
  shStockError.value = '';
  shStockSearched.value = true;
  try {
    var period = selectedPeriod.value || shareholdersLatestPeriod.value;
    var res = await fetch('/api/shareholders/' + code + '?period=' + period);
    var json = await res.json();
    if (json.status === 'ok' && json.data && json.data.length) {
      shStockResult.value = json.data;
      shStockActiveLabel.value = code;
      window.Vue.nextTick(function() { renderStockDetailChart(); });
    } else {
      shStockResult.value = [];
      shStockError.value = 'Data tidak ditemukan untuk ' + code;
    }
  } catch(e) {
    shStockError.value = 'Gagal memuat: ' + e.message;
    shStockResult.value = [];
  } finally {
    shStockLoading.value = false;
  }
}
function selectStockShareholder(code) {
  shStockQuery.value = code;
  // Find and set company name
  var found = shStockList.value.find(function(s) { return s.stock_code === code; });
  shStockActiveName.value = found ? (found.stock_name || '') : '';
  searchStockShareholders();
}
function filterStockGrid() {
  // Called on @input — clears previous result when typing new query
  if (shStockResult.value.length && shStockQuery.value.toUpperCase().trim() !== (shStockActiveLabel.value || '')) {
    shStockResult.value = [];
    shStockActiveName.value = '';
  }
}

// ── Watchlist ──
async function loadWatchlistData() {
  try {
    var data = await cachedFetch('/api/watchlist/1', 300000);
    watchlist.value = (data.watchlist || []).map(function(w) { return { code: w.stock_code || w.code || '', chg: 0 }; });
    ltWatchlist.value = (data.watchlist || []).map(function(w) { return { code: w.stock_code || w.code || '', name: '', chg: 0, volume: '-', sector: '-' }; });
    watchlist.value.forEach(function(w) {
      fetch('/api/stock/' + w.code).then(function(r) { return r.json(); }).then(function(d) { w.chg = d.change_pct || 0; }).catch(function() {});
    });
  } catch(e) { console.error('Watchlist load failed:', e); }
}

// ── Day Trading ──
async function loadDayTradingData() {
  try {
    var json = await cachedFetch('/api/day-trade/candidates', 300000);
    if (!json) { console.warn('Day trade load timeout'); return; }
    var candidates = (json.data && json.data.candidates) || [];
    var signalMap = { ENTER: { cls: 'success' }, WAIT: { cls: 'warning' }, AVOID: { cls: 'danger' }, HOLD: { cls: 'accent' } };
    dayTradingSignals.value = candidates.map(function(c) {
      var sig = signalMap[c.action] || signalMap.WAIT;
      return { code: c.stock_code, signal: c.action, signalClass: sig.cls, confidence: c.confidence || 0, price: c.current_price ? 'Rp ' + Number(c.current_price).toLocaleString('id') : '-', entry: c.entry_price ? 'Rp ' + Number(c.entry_price).toLocaleString('id') : '-', exit: c.target_profit ? 'Rp ' + Number(c.target_profit).toLocaleString('id') : '-' };
    });
    dayTradingCandidates.value = candidates.map(function(c) {
      return { stock: c.stock_code, signal: c.action, signalClass: signalMap[c.action] ? signalMap[c.action].cls : 'warning', conf: c.confidence || 0, entry: c.entry_price ? Number(c.entry_price).toLocaleString('id') : '-', tp: c.target_profit ? Number(c.target_profit).toLocaleString('id') : '-', cl: c.cut_loss ? Number(c.cut_loss).toLocaleString('id') : '-', volRatio: c.volume_ratio ? c.volume_ratio.toFixed(1) + 'x' : '-', foreignFlow: c.foreign_flow_status || '-', action: c.action === 'ENTER' ? 'Buy' : 'Watch' };
    });
    bpjsSignals.value = dayTradingSignals.value.slice(0, 4);
  } catch(e) { console.error('Day trade load failed:', e); }
}

// ── Foreign Flow ──
async function loadForeignFlowData() {
  try {
    var json = await cachedFetch('/api/foreign-flow/summary', 900000);
    if (!json) { console.warn('Foreign flow load timeout'); return; }
    var acc = (json.data && json.data.top_accumulating) || [];
    longTermSignals.value = acc.map(function(a) {
      return { code: a.stock_code, signal: a.strength === 'strong' ? 'Active Accum' : a.strength === 'moderate' ? 'Accum Watch' : 'Early Accum', signalClass: a.strength === 'strong' ? 'accent' : 'warning', confidence: Math.min(99, Math.round((a.accumulation_days || 0) * 3 + 50)), entryZone: a.cumulative_net ? 'Rp ' + Number(a.cumulative_net/1000000).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : 'N/A' };
    });
    ltAccumulation.value = acc.map(function(a) {
      return { code: a.stock_code, phase: a.strength === 'strong' ? 'Active Accum' : a.strength === 'moderate' ? 'Accum Watch' : 'Early Accum', signalClass: a.strength === 'strong' ? 'accent' : 'warning', confidence: Math.min(99, Math.round((a.accumulation_days || 0) * 3 + 50)), entryZone: a.cumulative_net ? Number(a.cumulative_net/1000000).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : 'N/A', accumDays: a.accumulation_days || 0, rsStatus: a.strength || 'Neutral' };
    });
  } catch(e) { console.error('Foreign flow load failed:', e); }
}

// ── Analysis History ──
async function loadAnalysisHistory() {
  try {
    var json = await cachedFetch('/api/analysis-history?limit=20', 900000);
    var history = json.history || [];
    if (history.length) {
      var wins = history.filter(function(h) { return h.result === 'win' || h.result === 'success'; });
      var total = history.length;
      var winRate = total ? Math.round(wins.length / total * 100) : 0;
      aiPerf.value = { accuracy: winRate + '%', accuracyChange: '-', winRate: winRate + '%', winRateChange: '-', avgProfit: history.reduce(function(a, h) { return a + (h.profit_pct || 0); }, 0) / total + '%', totalPredictions: String(total) };
      var fmt = history.map(function(h) {
        return { code: h.stock_code || h.code || '-', signal: h.prediction || h.signal || 'HOLD', signalClass: (h.prediction === 'BUY' || h.prediction === 'ENTER') ? 'success' : h.prediction === 'SELL' ? 'danger' : 'warning', confidence: h.confidence || 50, result: h.result === 'win' ? 'Win' : h.result === 'loss' ? 'Loss' : 'Pending', resultClass: h.result === 'win' ? 'success' : h.result === 'loss' ? 'danger' : 'warning', profit: (h.profit_pct >= 0 ? '+' : '') + (h.profit_pct || 0) + '%', profitClass: (h.profit_pct || 0) >= 0 ? 'profit-positive' : 'profit-negative', date: h.created_at ? h.created_at.slice(5, 10) : '-' };
      });
      predictions.value = fmt.slice(0, 5);
      allPredictions.value = fmt;
      dayTradingHistory.value = fmt.filter(function(h) { return h.code; }).map(function(h) { return { date: h.date, stock: h.code, entry: '-', exit: '-', profit: h.profit, profitClass: h.profitClass, result: h.result, resultClass: h.resultClass }; });
    }
  } catch(e) { console.error('Analysis history load failed:', e); }
}

// ── Alerts ──
async function loadAlerts() {
  try {
    var json = await cachedFetch('/api/alerts?limit=20', 300000);
    settingsAlerts.value = (json.alerts || []).map(function(a) { return { stock: a.stock_code || a.code || '-', type: a.alert_type || a.type || 'Price Alert', condition: a.condition || '-', status: a.status || 'Inactive' }; });
  } catch(e) { console.error('Alerts load failed:', e); }
}

// ── UI Actions ──
var _refreshIntervals = {};

function startAutoRefresh() {
  stopAutoRefresh();

  // Dashboard market — 2 menit
  _refreshIntervals.dashboard = setInterval(function() {
    if (typeof invalidateCache === 'function') {
      invalidateCache('/api/market');
      invalidateCache('/api/top-');
      invalidateCache('/api/sector');
    }
    loadMarketSummary();
    loadTopMovers();
    loadSectors();
  }, 2 * 60 * 1000);

  // Day Trading — 5 menit
  _refreshIntervals.daytrading = setInterval(function() {
    if (typeof invalidateCache === 'function') {
      invalidateCache('/api/day-trade');
    }
    loadDayTradingData();
  }, 5 * 60 * 1000);

  // Long Term — 15 menit
  _refreshIntervals.longterm = setInterval(function() {
    if (typeof invalidateCache === 'function') {
      invalidateCache('/api/long-term');
      invalidateCache('/api/foreign-flow');
    }
    loadForeignFlowData();
  }, 15 * 60 * 1000);
}

function stopAutoRefresh() {
  Object.values(_refreshIntervals).forEach(clearInterval);
  _refreshIntervals = {};
}
function mockScan() {
  loadDayTradingData();
  onCacheInvalidate('/api/day-trade');
  currentTab.value = 'signals';
}
function mockSave() {
  onCacheInvalidate('/api/alerts');
  onCacheInvalidate('/api/settings');
  alert('Settings saved (local only).');
}
function addAlert() {
  if (!newAlertStock.value || !newAlertCondition.value) return;
  settingsAlerts.value.push({ stock: newAlertStock.value, type: newAlertType.value, condition: newAlertCondition.value, status: 'Active' });
  newAlertStock.value = ''; newAlertType.value = 'Price Alert'; newAlertCondition.value = '';
  onCacheInvalidate('/api/alerts');
}
function removeAlert(alert) {
  var idx = settingsAlerts.value.indexOf(alert);
  if (idx > -1) settingsAlerts.value.splice(idx, 1);
  onCacheInvalidate('/api/alerts');
}
async function selectStock(item) {
  try {
    var res = await fetch('/api/analyze/' + item.code);
    if (!res.ok) throw new Error('Fetch failed');
    var data = await res.json();
    selectedStock.value = {
      code: item.code, name: item.name || data.stock_name || '', price: data.price ? 'Rp ' + Number(data.price).toLocaleString('id') : '-', chg: data.change_pct || 0,
      rsi: data.rsi != null ? String(data.rsi) : '-', rsiLabel: data.rsi_status || '-', macd: data.macd != null ? (data.macd >= 0 ? '+' : '') + Number(data.macd).toFixed(1) : '-',
      ma20: data.ma20 ? 'Rp ' + Number(data.ma20).toLocaleString('id') : '-', ma50: data.ma50 ? 'Rp ' + Number(data.ma50).toLocaleString('id') : '-', bbUpper: '-', bbLower: '-',
      r2: data.resistance ? 'Rp ' + Number(data.resistance * 1.05).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-', r1: data.resistance ? 'Rp ' + Number(data.resistance).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-',
      pivot: data.price ? 'Rp ' + Number(data.price).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-', s1: data.support ? 'Rp ' + Number(data.support).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-', s2: data.support ? 'Rp ' + Number(data.support * 0.95).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-',
      volume: data.volume ? Number(data.volume).toLocaleString('id') : '-', score: data.confidence || item.score || 50, confidence: data.confidence || item.score || 50,
      recommendation: data.recommendation || 'HOLD', signalClass: (data.recommendation === 'BUY' || data.recommendation === 'ENTER') ? 'success' : (data.recommendation === 'SELL') ? 'danger' : 'warning',
      analysis: data.full_analysis || data.reason || 'Analysis not available.',
    };
  } catch(e) {
    console.error('Analyze failed:', e);
    selectedStock.value = { code: item.code, name: item.name || '', price: '-', chg: 0, rsi: '-', rsiLabel: '-', macd: '-', ma20: '-', ma50: '-', bbUpper: '-', bbLower: '-', r2: '-', r1: '-', pivot: '-', s1: '-', s2: '-', volume: '-', score: item.score || 50, confidence: item.score || 50, recommendation: 'HOLD', signalClass: 'warning', analysis: 'Gagal mengambil data analisis dari server.' };
  }
  currentTab.value = 'detail';
}
async function addComparison() {
  if (!comparisonAddCode.value) return;
  try {
    var res = await fetch('/api/analyze/' + comparisonAddCode.value);
    if (!res.ok) throw new Error('fetch failed');
    var d = await res.json();
    comparisonStocks.value.push({ code: comparisonAddCode.value, price: d.price ? Number(d.price).toLocaleString('id') : '-', chg: d.change_pct != null ? (d.change_pct >= 0 ? '+' : '') + d.change_pct + '%' : '0%', rsi: d.rsi != null ? String(d.rsi) : '50', macd: d.macd != null ? (d.macd >= 0 ? '+' : '') + Number(d.macd).toFixed(1) : '0', volume: d.volume ? Number(d.volume).toLocaleString('id') : '-', score: String(d.confidence || 50), rec: d.recommendation || 'HOLD' });
  } catch(e) { console.error('Comparison add failed:', e); }
  comparisonAddCode.value = '';
}

// ── Market Reports ──
async function loadMarketReports() {
  try {
    var json = await cachedFetch('/api/market-reports?limit=500', 3600000);
    var full = (json.data || []).filter(function(r) { return r.type === 'full' || r.type === 'akhir_sesi' || r.type === 'sesi1'; });
    if (mrFilter.value !== 'all') { mrReports.value = full.filter(function(r) { return r.type === mrFilter.value; }); }
    else { mrReports.value = full; }
    if (full.length) { mrExpandedMonths.value[full[0].date.substring(0, 7)] = true; }
    var dataForStats = mrFilter.value !== 'all' ? mrReports.value : full;
    var ihsgVals = dataForStats.map(function(r) { return r.ihsg_change; }).filter(function(v) { return v !== null; });
    var avgIHSG = ihsgVals.length ? (ihsgVals.reduce(function(a,b) { return a+b; }, 0) / ihsgVals.length) : 0;
    var allForeignStocks = new Set();
    dataForStats.forEach(function(r) { (r.foreign_buy || []).forEach(function(s) { allForeignStocks.add(s.stock); }); });
    var redDays = ihsgVals.filter(function(v) { return v < 0; }).length;
    mrStats.value = { totalReports: dataForStats.length, avgIHSG: Math.round(avgIHSG * 10) / 10, foreignStocks: allForeignStocks.size, redDays: redDays };
    mrForeignStocks.value = buildMrStockTable('foreign_buy');
    mrLocalStocks.value = buildMrStockTable('local_buy');
    setTimeout(function() { renderMrCharts(full); }, 100);
    mrReportsLoading.value = false;
  } catch(e) { console.error('Market report load failed:', e); mrReportsLoading.value = false; }
}

async function loadMrAnalysis() {
  mrLoadingAnalysis.value = true;
  try {
    var json = await cachedFetch('/api/market-report-analysis', 3600000);
    if (json.status === 'ok' && json.analysis) mrAnalysis.value = json.analysis;
  } catch(e) { console.error('Analysis load failed:', e); }
  mrLoadingAnalysis.value = false;
}

async function loadForeignOverview() {
  try {
    var json = await cachedFetch('/api/market-reports?limit=5', 3600000);
    var reports = json.data || [];
    if (!reports.length) return;
    var latest = reports[0];
    var fb = latest.foreign_buy || [], lb = latest.local_buy || [];
    var map = {};
    fb.forEach(function(s) { map[s.stock] = { stock: s.stock, foreignBuy: s.value, localBuy: 0 }; });
    lb.forEach(function(s) { if (map[s.stock]) map[s.stock].localBuy = s.value; else map[s.stock] = { stock: s.stock, foreignBuy: 0, localBuy: s.value }; });
    var stocks = Object.values(map).map(function(s) { return Object.assign({}, s, { net: s.foreignBuy - s.localBuy }); });
    foreignOverviewStocks.value = stocks.filter(function(s) { return s.net > 0; }).sort(function(a,b) { return b.net - a.net; }).slice(0, 10);
    pahlawanBursaStocks.value = stocks.filter(function(s) { return s.net < 0; }).sort(function(a,b) { return (b.localBuy - b.foreignBuy) - (a.localBuy - a.foreignBuy); }).slice(0, 10);
    dailyNetTotal.value = stocks.reduce(function(sum, s) { return sum + s.net; }, 0);
    foreignStockCount.value = stocks.filter(function(s) { return s.net > 0; }).length;
    foreignActivitySummary.value = { totalForeign: fb.reduce(function(a, s) { return a + s.value; }, 0), totalLocal: lb.reduce(function(a, s) { return a + s.value; }, 0), date: latest.date };
  } catch(e) { console.error('Foreign overview load failed:', e); }
}

async function loadBacktest() {
  mrBtLoading.value = true; mrBtError.value = null;
  try {
    var json = await cachedFetch('/api/market-backtest', 3600000);
    if (json.status === 'ok') mrBtData.value = json;
    else mrBtError.value = 'Gagal muat data backtest';
  } catch(e) { console.error('Backtest load failed:', e); mrBtError.value = 'Backtest error: ' + e.message; }
  mrBtLoading.value = false;
}

function switchMrTab(tab) {
  currentTab.value = tab;
  if (tab === 'overview') setTimeout(function() { renderMrCharts(mrReports.value); }, 100);
  if (tab === 'analysis' && !mrAnalysis.value) loadMrAnalysis();
  if (tab === 'backtest' && !mrBtData.value) loadBacktest();
}

function setMrFilter(filter) {
  mrFilter.value = filter;
  loadMarketReports();
}

function switchView(view, tab) {
  currentView.value = view;
  if (view === 'marketreports' && !_loadedViews.marketreports) { loadMarketReports(); _loadedViews.marketreports = true; }
  if (view === 'daytrading' && !_loadedViews.daytrading) loadDayTradingView();
  if (view === 'longterm' && !_loadedViews.longterm) loadLongTermView();
  if (view === 'analysis' && !_loadedViews.analysis) loadAnalysisView();
  if (view === 'shareholders' && !_loadedViews.shareholders) loadShareholdersView();
  var firstTabs = { dashboard: 'overview', daytrading: 'signals', longterm: 'accumulation', analysis: 'search', shareholders: 'overview', settings: 'general', marketreports: 'overview' };
  _viewChanging = true;
  currentTab.value = tab || firstTabs[view] || 'overview';
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

// ── Shareholder search functions ──
async function searchShareholdersByStock() {
  var q = shStockQuery.value.trim();
  if (!q) return;
  shStockLoading.value = true; shStockError.value = ''; shStockSearched.value = true;
  try {
    var period = shareholdersLatestPeriod.value || 'FEB2026';
    var res = await fetch('/api/shareholders/' + q.toUpperCase() + '?period=' + period);
    var data = await res.json();
    if (data.status === 'ok') shStockResult.value = data.data;
    else { shStockError.value = 'Gagal memuat data'; shStockResult.value = []; }
  } catch(e) { shStockError.value = 'Gagal mengambil data: ' + e.message; shStockResult.value = []; }
  shStockLoading.value = false;
}
async function onShStockSelect() {
  var val = shStockSelected.value;
  if (!val) return;
  shStockQuery.value = ''; shStockLoading.value = true; shStockError.value = ''; shStockSearched.value = true;
  try {
    var period = shareholdersLatestPeriod.value || 'FEB2026';
    var res = await fetch('/api/shareholders/' + val + '?period=' + period);
    var data = await res.json();
    if (data.status === 'ok') shStockResult.value = data.data;
    else { shStockError.value = 'Gagal memuat data'; shStockResult.value = []; }
  } catch(e) { shStockError.value = 'Gagal mengambil data: ' + e.message; shStockResult.value = []; }
  shStockLoading.value = false;
}
async function searchShareholdersByHolder() {
  var name = shHolderQuery.value.trim().toUpperCase();
  if (!name) return;
  shHolderLoading.value = true;
  shHolderError.value = '';
  shHolderSearched.value = true;
  try {
    var period = selectedPeriod.value || shareholdersLatestPeriod.value || 'FEB2026';
    var res = await fetch('/api/shareholders/search/' + encodeURIComponent(name) + '?period=' + period);
    var json = await res.json();
    if (json.status === 'ok' && json.data && json.data.length) {
      shHolderResult.value = json.data;
      window.Vue.nextTick(function() { renderHolderPortfolioChart(); });
    } else {
      shHolderResult.value = [];
      shHolderError.value = 'Data tidak ditemukan untuk "' + name + '"';
    }
  } catch(e) {
    shHolderError.value = 'Gagal memuat: ' + e.message;
    shHolderResult.value = [];
  } finally {
    shHolderLoading.value = false;
  }
}
function selectHolder(name) {
  shHolderQuery.value = name;
  searchShareholdersByHolder();
}

// ── Bootstrap load all ──
async function loadAllDashboardData() {
  await Promise.allSettled([
    loadMarketSummary(), loadTopMovers(), loadSectors(), loadStocks(),
    loadWatchlistData(), loadDayTradingData(), loadForeignFlowData(),
    loadAnalysisHistory(), loadAlerts(), loadShareholders(),
  ]);
};

// ⚠ DEPRECATED — kept for reference, use per-view loaders instead

