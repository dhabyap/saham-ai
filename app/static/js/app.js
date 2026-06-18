// ─── Vue App Entry ───
// Depends on: state.js, utils.js, charts.js, loaders.js

const { createApp, onMounted, watch } = Vue;

let _viewChanging = false;

const VIEW_PATH_MAP = {
  '/dashboard': 'dashboard',
  '/daytrading': 'daytrading',
  '/longterm': 'longterm',
  '/analysis': 'analysis',
  '/shareholders': 'shareholders',
  '/settings': 'settings',
  '/market-reports': 'marketreports',
};

function navigateFromHash() {
  const hash = window.location.hash.replace('#', '');
  if (!hash) return null;
  const parts = hash.split('/');
  const view = parts[0] in VIEW_PATH_MAP ? parts[0] : null;
  if (!view && ['dashboard','daytrading','longterm','analysis','shareholders','settings','marketreports'].includes(parts[0])) {
    return { view: parts[0], tab: parts[1] || null };
  }
  if (view) return { view, tab: parts[1] || null };
  return null;
}

function getViewFromUrl() {
  const fromHash = navigateFromHash();
  if (fromHash && fromHash.view) return fromHash;
  const path = window.location.pathname.replace(/\/$/, '');
  if (VIEW_PATH_MAP[path]) return { view: VIEW_PATH_MAP[path], tab: null };
  const params = new URLSearchParams(window.location.search);
  const view = params.get('view');
  const validViews = ['dashboard','daytrading','longterm','analysis','shareholders','settings','marketreports'];
  if (validViews.includes(view)) return { view, tab: null };
  return null;
}

function syncViewFromUrl() {
  const result = getViewFromUrl();
  if (result && result.view) {
    currentView.value = result.view;
    _viewChanging = true;
    currentTab.value = result.tab || 'overview';
    if (result.view === 'marketreports') loadMarketReports();
  }
}

createApp({
  setup() {
    watch(currentTheme, (val) => {
      localStorage.setItem('dashboard-theme', val);
      document.documentElement.setAttribute('data-theme', val);
    });

    watch(currentTab, (tab) => {
      if (currentView.value) {
        const hash = `#${currentView.value}/${tab}`;
        if (_viewChanging) {
          history.pushState(null, '', hash);
          _viewChanging = false;
        } else if (window.location.hash !== hash) {
          history.replaceState(null, '', hash);
        }
      }
    });

    onMounted(() => {
      const saved = localStorage.getItem('dashboard-theme');
      if (saved) currentTheme.value = saved;
      document.documentElement.setAttribute('data-theme', currentTheme.value);
      const d = new Date();
      dateStr.value = d.toLocaleDateString('en-ID', { month: 'short', day: 'numeric', year: 'numeric' });
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') searchOpen.value = false;
      });
      syncViewFromUrl();
      loadForeignOverview();
      window.addEventListener('hashchange', () => syncViewFromUrl());
      loadMarketReports();
      loadStocks();
      loadWatchlistData();
    });

    return {
      // Appearance
      currentTheme, themes, headerTitle,
      // Navigation
      currentView, navItems, currentTab, switchView, switchMrTab,
      // Search
      searchQuery, searchOpen, sidebarOpen, filteredStocks, allStocks,
      toggleSidebar, closeSearch, onSearchInput,
      // Date
      dateStr,
      // Market Reports
      mrReports, mrReportsLoading, mrStats, mrForeignStocks, mrLocalStocks, mrFilter, setMrFilter,
      mrAnalysis, mrLoadingAnalysis, mrStocksLoading, loadMrAnalysis,
      // Backtest
      mrBtData, mrBtLoading, mrBtError, loadBacktest,
      // Month groups
      mrMonths, mrExpandedMonths, toggleMonth,
      // Foreign stock table
      mrNetForeign, mrSortKey, mrSortDir, mrSortedForeign,
      toggleMrSort, mrSortIcon,
      // Foreign overview sidebar
      foreignOverviewStocks, pahlawanBursaStocks, dailyNetTotal,
      foreignStockCount, foreignActivitySummary,
      loadForeignOverview,
      // Watchlist sidebar
      watchlist,
      // Formatters
      formatRp,
      // Data load (kept for template)
      loadMarketReports,
      // Theme
      switchTheme,
    };
  }
}).mount('#app');
