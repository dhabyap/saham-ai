// ─── Vue App Entry ───
// Depends on: state.js, utils.js, charts.js, loaders.js

const { createApp, onMounted, watch } = Vue;

let _viewChanging = false;

function navigateFromHash() {
  const hash = window.location.hash.replace('#', '');
  if (!hash) return null;
  const parts = hash.split('/');
  const view = parts[0] === 'marketreports' ? 'marketreports' : null;
  const tab = parts[1] || null;
  return { view, tab };
}

function getViewFromUrl() {
  const fromHash = navigateFromHash();
  if (fromHash && fromHash.view) return fromHash;
  const path = window.location.pathname.replace(/\/$/, '');
  const pathMap = { '/market-reports': 'marketreports' };
  if (pathMap[path]) return { view: pathMap[path], tab: null };
  const params = new URLSearchParams(window.location.search);
  const view = params.get('view');
  if (view === 'marketreports') return { view: 'marketreports', tab: null };
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
