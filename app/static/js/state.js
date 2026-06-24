// ─── Vue Reactive State ───
var _a = Vue, ref = _a.ref, computed = _a.computed;

// ── Navigation / Appearance ──
var currentTheme = ref('neumorphism');
var currentView = ref('dashboard');
var currentTab = ref('overview');
var searchQuery = ref('');
var sidebarOpen = ref(true);
var searchOpen = ref(false);
var dateStr = ref('');

// ── Lazy Load tracking ──
var _loadedViews = {};
var dashboardLoading = ref(true);
var daytradingLoading = ref(false);
var longtermLoading = ref(false);
var analysisLoading = ref(false);
var shareholdersLoading = ref(false);
var mrLoading = ref(false);

var themes = [
  { id: 'neumorphism', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'classy', label: 'Classy' },
];

var navItems = [
  { view: 'dashboard',     icon: '&#9751;', label: 'Dashboard' },
  { view: 'daytrading',    icon: '&#8644;', label: 'Day Trading' },
  { view: 'longterm',      icon: '&#9670;', label: 'Long Term' },
  { view: 'analysis',      icon: '&#9776;', label: 'Analysis' },
  { view: 'shareholders',  icon: '&#128101;', label: 'Shareholders' },
  { view: 'brokerdata',    icon: '&#128176;', label: 'Broker Data' },
  { view: 'marketreports', icon: '&#128202;', label: 'Market Reports' },
  { view: 'settings',      icon: '&#9881;', label: 'Settings' },
];

var headerTitle = computed(function() {
  var map = {
    dashboard: 'Dashboard', daytrading: 'Day Trading', longterm: 'Long Term',
    analysis: 'Analysis', shareholders: 'Shareholders', brokerdata: 'Broker Data',
    settings: 'Settings',
    marketreports: 'Market Reports',
  };
  return map[currentView.value] || 'Dashboard';
});

// ── Dashboard Overview ──
var overviewLoading = ref(true);
var stocksLoading = ref(false);

// ── Per-View Loading States ──
var daytradingLoading = ref(true);
var longtermLoading = ref(true);
var shareholdersLoading = ref(true);
var analysisLoading = ref(true);
var mrReportsLoading = ref(true);
var foreignOverviewStocks = ref([]);

// ── Broker Data ──
var bdData = ref(null);
var bdLoading = ref(false);
var bdError = ref(null);
var bdStockQuery = ref('');
var bdAvailable = ref([]);
var bdCurrentStock = ref(null);
var bdShowSuggestions = ref(false);
var bdFiltered = computed(function () {
  if (!bdStockQuery.value || !bdAvailable.value.length) return [];
  var q = bdStockQuery.value.toUpperCase();
  return bdAvailable.value.filter(function (s) {
    return s.stock_code.indexOf(q) !== -1;
  }).slice(0, 20);
});
var bdHighlight = ref(-1);
var bdSearchFocused = ref(false);

function bdFmt(v) {
  if (!v) return '0';
  var s = String(v).replace(/,/g, '');
  return s.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

var pahlawanBursaStocks = ref([]);
var dailyNetTotal = ref(0);
var foreignStockCount = ref(0);
var foreignActivitySummary = ref(null);

var market = ref({
  fgi: { value: 50, label: 'Neutral' },
  advancing: { count: 0, change: 0, pct: '0%' },
  declining: { count: 0, change: 0, pct: '0%' },
  avgChange: '0%', totalVolume: '0', volumeChange: '-',
  status: 'Loading...', hours: '-',
});

var aiPerf = ref({
  accuracy: '-', accuracyChange: '-', winRate: '-',
  winRateChange: '-', avgProfit: '-', totalPredictions: '-',
});
var aiPerfDetails = ref([]);
var movers = ref({ gainers: [], losers: [], volume: [] });
var allGainers = ref([]);
var allLosers = ref([]);
var allVolume = ref([]);
var bpjsSignals = ref([]);
var longTermSignals = ref([]);
var sectors = ref([]);
var predictions = ref([]);
var allPredictions = ref([]);

// ── Day Trading ──
var dayTradingSignals = ref([]);
var dayTradingCandidates = ref([]);
var dayTradingHistory = ref([]);

// ── Long Term ──
var ltAccumulation = ref([]);
var ltPortfolio = ref([]);
var ltWatchlist = ref([]);

// ── Watchlist / Search ──
var watchlist = ref([]);
var allStocks = ref([]);

var filteredStocks = computed(function() {
  var q = searchQuery.value.toLowerCase();
  if (!q) return allStocks.value;
  return allStocks.value.filter(function(s) {
    return s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q);
  });
});

// ── Analysis ──
var analysisQuery = ref('');
var analysisSector = ref('All');
var analysisSectors = ['All', 'Financials', 'Technology', 'Energy', 'Consumer Cycl.', 'Healthcare'];
var analysisStocks = ref([]);

var filteredAnalysis = computed(function() {
  var items = analysisStocks.value;
  if (analysisSector.value !== 'All') {
    items = items.filter(function(s) { return s.sector === analysisSector.value; });
  }
  if (analysisQuery.value) {
    var q = analysisQuery.value.toLowerCase();
    items = items.filter(function(s) { return s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q); });
  }
  return items;
});

var selectedStock = ref({
  code: '-', name: '-', price: '-', chg: 0,
  rsi: '-', rsiLabel: '-', macd: '-',
  ma20: '-', ma50: '-', bbUpper: '-', bbLower: '-',
  r2: '-', r1: '-', pivot: '-', s1: '-', s2: '-',
  volume: '-', score: 0, confidence: 0,
  recommendation: 'HOLD', signalClass: 'warning',
  analysis: 'Select a stock to analyze.',
});

var comparisonStocks = ref([]);
var comparisonAddCode = ref('');

var comparisonRows = computed(function() { return [
  { label: 'Price', getValue: function(s) { return s.price; } },
  { label: 'Change %', getValue: function(s) { return s.chg; }, getClass: function(s) { return s.chg && s.chg.startsWith('+') ? 'profit-positive' : 'profit-negative'; } },
  { label: 'RSI (14)', getValue: function(s) { return s.rsi; } },
  { label: 'MACD', getValue: function(s) { return s.macd; }, getClass: function(s) { return s.macd && s.macd.startsWith('+') ? 'profit-positive' : 'profit-negative'; } },
  { label: 'Volume', getValue: function(s) { return s.volume; } },
  { label: 'AI Score', getValue: function(s) { return s.score; }, getClass: function(s) { return parseInt(s.score) >= 80 ? 'profit-positive' : parseInt(s.score) >= 60 ? '' : 'profit-negative'; } },
  { label: 'Recommendation', getValue: function(s) { return s.rec; }, getClass: function(s) { return s.rec === 'BUY' ? 'profit-positive' : s.rec === 'SELL' ? 'profit-negative' : ''; } },
]; });

var comparisonAvailable = computed(function() {
  var used = new Set(comparisonStocks.value.map(function(s) { return s.code; }));
  return allStocks.value.filter(function(s) { return !used.has(s.code); }).map(function(s) { return s.code; });
});

// ── Shareholders ──
var shareholdersStats = ref({ total_records: 0, total_stocks: 0, total_holders: 0, top_holder: '-', period: 'all' });
var shareholdersPeriods = ref([]);
var shareholdersLatestPeriod = ref('');
var shareholdersError = ref('');
var topShareholders = ref([]);
var shareholderSearchQuery = ref('');
var shareholderSearchResults = ref([]);
var shareholderStockQuery = ref('');
var shareholderStockResults = ref([]);

var shStockQuery = ref('');
var shStockResult = ref([]);
var shStockLoading = ref(false);
var shStockError = ref('');
var shStockSearched = ref(false);
var shStockList = ref([]);
var shStockSelected = ref('');
var shStockActiveLabel = computed(function() {
  if (shStockResult.value.length && shStockSelected.value) return shStockSelected.value;
  if (shStockResult.value.length && shStockQuery.value) return shStockQuery.value.toUpperCase();
  return '';
});
var shStockActiveName = ref('');

// Live filter for Per Emiten grid
var filteredStockList = computed(function() {
  var q = (shStockQuery.value || '').toUpperCase().trim();
  if (!q) return shStockList.value;
  return shStockList.value.filter(function(s) {
    return s.stock_code.indexOf(q) !== -1 || (s.stock_name || '').toUpperCase().indexOf(q) !== -1;
  });
});

// Overview table search
var shOverviewQuery = ref('');
var shFilteredOverview = computed(function() {
  var q = (shOverviewQuery.value || '').toUpperCase().trim();
  if (!q) return shSortedTable.value;
  return shSortedTable.value.filter(function(s) {
    return s.stock_code.indexOf(q) !== -1;
  });
});

var shHolderQuery = ref('');
var shHolderResult = ref([]);
var shHolderLoading = ref(false);
var shHolderError = ref('');
var shHolderSearched = ref(false);
var popularHolders = ref([]);
var shHolderSelected = ref('');

// Live filter for Top Holders grid (like filteredStockList)
var filteredHolders = computed(function() {
  var q = (shHolderQuery.value || '').toUpperCase().trim();
  if (!q) return popularHolders.value;
  return popularHolders.value.filter(function(h) {
    return (h.shareholder_name || '').toUpperCase().indexOf(q) !== -1;
  });
});
var selectedPeriod = ref(''); // selected period for shareholders
// ── Shareholders Enhanced ──
var shDistribution = ref(null);
var shTopStocks = ref([]);
var shConcentration = ref([]);
var shDetailStats = ref(null);
var shInsight = ref(null);
var shInsightLoading = ref(false);
var shInsightError = ref('');
var shUploadPeriod = ref('');
var shUploadFile = ref(null);
var shUploadLoading = ref(false);
var shUploadError = ref('');
var shUploadResult = ref(null);
var shDistLoading = ref(false);
var shScatterData = ref([]);
var shSortKey = ref('holders');
var shSortOrder = ref('desc');
var shSortedTable = computed(function() {
  var data = shScatterData.value || [];
  var key = shSortKey.value;
  var order = shSortOrder.value;
  return data.slice().sort(function(a, b) {
    var va = a[key], vb = b[key];
    if (typeof va === 'string') return order === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    return order === 'asc' ? (va - vb) : (vb - va);
  });
});
function sortTable(key) {
  if (shSortKey.value === key) shSortOrder.value = shSortOrder.value === 'asc' ? 'desc' : 'asc';
  else { shSortKey.value = key; shSortOrder.value = 'desc'; }
}
var shStockDetailData = ref(null);
var shStockDetailLoading = ref(false);
var shHolderPortfolio = ref(null);
var shHolderPortfolioLoading = ref(false);
var shForceData = ref(null);
var shHolderSelected = ref(null);
var shForceLoading = ref(false);
var shForceSelected = ref(null);

var shHolderActiveName = computed(function() {
  if (shHolderResult.value.length && shHolderSearched.value) return shHolderQuery.value.toUpperCase();
  return '';
});

var filteredTopShareholders = computed(function() {
  var q = shareholderSearchQuery.value.toLowerCase();
  if (!q) return topShareholders.value;
  return topShareholders.value.filter(function(s) { return s.shareholder_name.toLowerCase().includes(q); });
});

// ── Market Reports ──
var mrReports = ref([]);
var mrStats = ref({ totalReports: 0, avgIHSG: 0, foreignStocks: 0, redDays: 0 });
var mrForeignStocks = ref([]);
var mrLocalStocks = ref([]);
var mrAnalysis = ref(null);
var mrLoadingAnalysis = ref(false);
var mrFilter = ref('all');
var mrBtData = ref(null);
var mrBtLoading = ref(false);
var mrBtError = ref(null);
var mrExpandedMonths = ref({});
var mrSortKey = ref('net');
var mrSortDir = ref('desc');

function toggleMrSort(key) {
  if (mrSortKey.value === key) {
    mrSortDir.value = mrSortDir.value === 'asc' ? 'desc' : 'asc';
  } else {
    mrSortKey.value = key;
    mrSortDir.value = key === 'stock' ? 'asc' : 'desc';
  }
}
function mrSortIcon(key) {
  if (mrSortKey.value !== key) return ' ↕';
  return mrSortDir.value === 'asc' ? ' ↑' : ' ↓';
}

var mrSortedForeign = computed(function() {
  var key = mrSortKey.value;
  var dir = mrSortDir.value === 'asc' ? 1 : -1;
  var list = mrNetForeign.value.slice().filter(function(x) { return x.net > 0; });
  return list.sort(function(a, b) {
    var va = a[key], vb = b[key];
    if (key === 'lastDate') { va = va || ''; vb = vb || ''; }
    if (typeof va === 'string') return va.localeCompare(vb) * dir;
    return (va - vb) * dir;
  });
});

var mrNetForeign = computed(function() {
  var map = {};
  mrReports.value.forEach(function(r) {
    (r.foreign_buy || []).forEach(function(s) {
      if (!map[s.stock]) map[s.stock] = { stock: s.stock, foreignTotal: 0, localTotal: 0, lastDate: r.date };
      map[s.stock].foreignTotal += s.value;
      if (r.date > map[s.stock].lastDate) map[s.stock].lastDate = r.date;
    });
    (r.local_buy || []).forEach(function(s) {
      if (!map[s.stock]) map[s.stock] = { stock: s.stock, foreignTotal: 0, localTotal: 0, lastDate: r.date };
      map[s.stock].localTotal += s.value;
      if (r.date > map[s.stock].lastDate) map[s.stock].lastDate = r.date;
    });
  });
  return Object.values(map).map(function(s) { return Object.assign({}, s, { net: s.foreignTotal - s.localTotal }); }).sort(function(a, b) { return b.net - a.net; });
});

var mrMonths = computed(function() {
  var groups = {};
  mrReports.value.forEach(function(r) {
    var m = r.date.substring(0, 7);
    if (!groups[m]) groups[m] = { key: m, label: '', reports: [] };
    groups[m].reports.push(r);
  });
  var monthNames = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
  return Object.keys(groups).sort().reverse().map(function(k) {
    var g = groups[k];
    var parts = k.split('-');
    g.label = monthNames[parseInt(parts[1])-1] + ' ' + parts[0];
    var ihsg = g.reports.map(function(r) { return r.ihsg_change; }).filter(function(v) { return v !== null; });
    g.count = g.reports.length;
    g.avgIHSG = ihsg.length ? ihsg.reduce(function(a,b) { return a+b; }, 0) / ihsg.length : null;
    g.redDays = ihsg.filter(function(v) { return v < 0; }).length;
    g.greenDays = ihsg.filter(function(v) { return v >= 0; }).length;
    g.foreignSet = new Set();
    g.reports.forEach(function(r) { (r.foreign_buy || []).forEach(function(s) { g.foreignSet.add(s.stock); }); });
    return g;
  });
});

function toggleMonth(key) {
  mrExpandedMonths.value[key] = !mrExpandedMonths.value[key];
}

// ── Settings ──
var settingsLanguage = ref('en');
var settingsRiskTolerance = ref('medium');
var settingsTargetProfit = ref('5');
var settingsEmailNotif = ref(true);
var settingsPushNotif = ref(true);
var settingsAlerts = ref([]);
var newAlertStock = ref('');
var newAlertType = ref('Price Alert');
var newAlertCondition = ref('');
