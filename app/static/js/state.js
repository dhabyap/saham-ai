// ─── Vue Reactive State ───
const { ref, computed } = Vue;

// ── Navigation ──
const currentTheme = ref('neumorphism');
const currentView = ref('marketreports');
const currentTab = ref('overview');
const searchQuery = ref('');
const sidebarOpen = ref(true);
const searchOpen = ref(false);
const dateStr = ref('');

const themes = [
  { id: 'neumorphism', label: 'Light' },
  { id: 'dark', label: 'Dark' },
  { id: 'classy', label: 'Classy' },
];

const navItems = [
  { view: 'marketreports', icon: '📊', label: 'Market Reports' },
];

const headerTitle = computed(() => 'Market Reports');

// ── Market Reports State ──
const mrReports = ref([]);
const mrReportsLoading = ref(true);
const mrStats = ref({ totalReports: 0, avgIHSG: 0, foreignStocks: 0, redDays: 0 });
const mrForeignStocks = ref([]);
const mrLocalStocks = ref([]);
const mrAnalysis = ref(null);
const mrLoadingAnalysis = ref(false);
const mrStocksLoading = ref(false);
const mrFilter = ref('all');
const mrBtData = ref(null);
const mrBtLoading = ref(false);
const mrBtError = ref(null);
const mrExpandedMonths = ref({});
const mrSortKey = ref('net');
const mrSortDir = ref('desc');

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

const mrSortedForeign = computed(() => {
  const key = mrSortKey.value;
  const dir = mrSortDir.value === 'asc' ? 1 : -1;
  const list = [...mrNetForeign.value].filter(x => x.net > 0);
  return list.sort((a, b) => {
    let va = a[key], vb = b[key];
    if (key === 'lastDate') { va = va || ''; vb = vb || ''; }
    if (typeof va === 'string') return va.localeCompare(vb) * dir;
    return (va - vb) * dir;
  });
});

const foreignOverviewStocks = ref([]);
const pahlawanBursaStocks = ref([]);
const dailyNetTotal = ref(0);
const foreignStockCount = ref(0);
const foreignActivitySummary = ref(null);

const mrNetForeign = computed(() => {
  const map = {};
  mrReports.value.forEach(r => {
    (r.foreign_buy || []).forEach(s => {
      if (!map[s.stock]) map[s.stock] = { stock: s.stock, foreignTotal: 0, localTotal: 0, lastDate: r.date };
      map[s.stock].foreignTotal += s.value;
      if (r.date > map[s.stock].lastDate) map[s.stock].lastDate = r.date;
    });
    (r.local_buy || []).forEach(s => {
      if (!map[s.stock]) map[s.stock] = { stock: s.stock, foreignTotal: 0, localTotal: 0, lastDate: r.date };
      map[s.stock].localTotal += s.value;
      if (r.date > map[s.stock].lastDate) map[s.stock].lastDate = r.date;
    });
  });
  return Object.values(map).map(s => ({
    ...s,
    net: s.foreignTotal - s.localTotal,
  })).sort((a, b) => b.net - a.net);
});

const mrMonths = computed(() => {
  const groups = {};
  mrReports.value.forEach(r => {
    const m = r.date.substring(0, 7);
    if (!groups[m]) groups[m] = { key: m, label: '', reports: [] };
    groups[m].reports.push(r);
  });
  const monthNames = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
  return Object.keys(groups).sort().reverse().map(k => {
    const g = groups[k];
    const [y, mo] = k.split('-');
    g.label = monthNames[parseInt(mo)-1] + ' ' + y;
    const ihsg = g.reports.map(r => r.ihsg_change).filter(v => v !== null);
    g.count = g.reports.length;
    g.avgIHSG = ihsg.length ? ihsg.reduce((a,b) => a+b, 0) / ihsg.length : null;
    g.redDays = ihsg.filter(v => v < 0).length;
    g.greenDays = ihsg.filter(v => v >= 0).length;
    g.foreignSet = new Set();
    g.reports.forEach(r => (r.foreign_buy || []).forEach(s => g.foreignSet.add(s.stock)));
    return g;
  });
});

function toggleMonth(key) {
  mrExpandedMonths.value[key] = !mrExpandedMonths.value[key];
}

// ── Watchlist / Search ──
const watchlist = ref([]);
const allStocks = ref([]);

const filteredStocks = computed(() => {
  const q = searchQuery.value.toLowerCase();
  if (!q) return allStocks.value;
  return allStocks.value.filter(s =>
    s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
  );
});
