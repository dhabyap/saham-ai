// ─── Vue App Entry Point ───
// Depends on: state.js, utils.js, charts.js, loaders.js (loaded via <script> before this)

var _vue = Vue, createApp = _vue.createApp, onMounted = _vue.onMounted, watch = _vue.watch;

var _viewChanging = false;

function navigateFromHash() {
  var hash = window.location.hash.replace('#', '');
  if (!hash) return null;
  var parts = hash.split('/');
  var validViews = ['dashboard', 'daytrading', 'longterm', 'analysis', 'shareholders', 'settings', 'marketreports'];
  var view = validViews.indexOf(parts[0]) !== -1 ? parts[0] : null;
  return { view: view, tab: parts[1] || null };
}

function getViewFromUrl() {
  var fromHash = navigateFromHash();
  if (fromHash && fromHash.view) return fromHash;
  var path = window.location.pathname.replace(/\/$/, '');
  var pathMap = { '/market-reports': 'marketreports', '/dashboard': 'dashboard', '/shareholders': 'shareholders' };
  if (pathMap[path]) return { view: pathMap[path], tab: null };
  var params = new URLSearchParams(window.location.search);
  var view = params.get('view');
  var validViews = ['dashboard', 'daytrading', 'longterm', 'analysis', 'shareholders', 'settings', 'marketreports'];
  if (validViews.indexOf(view) !== -1) return { view: view, tab: null };
  return null;
}

function syncViewFromUrl() {
  var result = getViewFromUrl();
  if (result && result.view) {
    currentView.value = result.view;
    var firstTabs = { dashboard: 'overview', daytrading: 'signals', longterm: 'accumulation', analysis: 'search', shareholders: 'overview', settings: 'general', marketreports: 'overview' };
    _viewChanging = true;
    currentTab.value = result.tab || firstTabs[result.view] || 'overview';
    if (result.view === 'marketreports') loadMarketReports();
  }
}

createApp({
  setup: function() {
    watch(currentTheme, function(val) {
      localStorage.setItem('dashboard-theme', val);
      document.documentElement.setAttribute('data-theme', val);
    });

    watch(currentTab, function(tab) {
      if (currentView.value) {
        var hash = '#' + currentView.value + '/' + tab;
        if (_viewChanging) { history.pushState(null, '', hash); _viewChanging = false; }
        else if (window.location.hash !== hash) { history.replaceState(null, '', hash); }
      }
    });

    onMounted(function() {
      var saved = localStorage.getItem('dashboard-theme');
      if (saved) currentTheme.value = saved;
      document.documentElement.setAttribute('data-theme', currentTheme.value);
      var d = new Date();
      dateStr.value = d.toLocaleDateString('en-ID', { month: 'short', day: 'numeric', year: 'numeric' });
      document.addEventListener('keydown', function(e) { if (e.key === 'Escape') searchOpen.value = false; });
      syncViewFromUrl();
      loadForeignOverview();
      window.addEventListener('hashchange', function() { syncViewFromUrl(); });
      // Lazy load: only dashboard data on mount, others load on demand
      loadDashboardData();
    });

    return {
      // Appearance
      currentTheme: currentTheme, themes: themes, headerTitle: headerTitle,
      // Navigation
      currentView: currentView, navItems: navItems, currentTab: currentTab,
      switchView: switchView, switchMrTab: switchMrTab,
      // Lazy loading states
      dashboardLoading: dashboardLoading,
      daytradingLoading: daytradingLoading,
      longtermLoading: longtermLoading,
      analysisLoading: analysisLoading,
      shareholdersLoading: shareholdersLoading,
      mrLoading: mrLoading,
      // Search / Sidebar
      searchQuery: searchQuery, searchOpen: searchOpen, sidebarOpen: sidebarOpen,
      filteredStocks: filteredStocks, allStocks: allStocks,
      toggleSidebar: toggleSidebar, closeSearch: closeSearch, onSearchInput: onSearchInput,
      dateStr: dateStr,
      // Loading States
      overviewLoading: overviewLoading, daytradingLoading: daytradingLoading,
      longtermLoading: longtermLoading, analysisLoading: analysisLoading,
      shareholdersLoading: shareholdersLoading, mrReportsLoading: mrReportsLoading,
      // Dashboard Overview
      foreignOverviewStocks: foreignOverviewStocks,
      pahlawanBursaStocks: pahlawanBursaStocks, dailyNetTotal: dailyNetTotal,
      foreignStockCount: foreignStockCount, foreignActivitySummary: foreignActivitySummary,
      market: market, aiPerf: aiPerf, aiPerfDetails: aiPerfDetails,
      movers: movers, allGainers: allGainers, allLosers: allLosers, allVolume: allVolume,
      bpjsSignals: bpjsSignals, longTermSignals: longTermSignals,
      sectors: sectors, predictions: predictions, allPredictions: allPredictions,
      // Day Trading
      dayTradingSignals: dayTradingSignals, dayTradingCandidates: dayTradingCandidates,
      dayTradingHistory: dayTradingHistory,
      // Long Term
      ltAccumulation: ltAccumulation, ltPortfolio: ltPortfolio, ltWatchlist: ltWatchlist,
      // Analysis
      analysisQuery: analysisQuery, analysisSector: analysisSector,
      analysisSectors: analysisSectors, analysisStocks: analysisStocks,
      filteredAnalysis: filteredAnalysis, selectedStock: selectedStock,
      selectStock: selectStock,
      comparisonStocks: comparisonStocks, comparisonRows: comparisonRows,
      comparisonAddCode: comparisonAddCode, comparisonAvailable: comparisonAvailable,
      addComparison: addComparison,
      // Shareholders
      shareholdersStats: shareholdersStats, shareholdersPeriods: shareholdersPeriods,
      shareholdersLatestPeriod: shareholdersLatestPeriod,
      shareholdersError: shareholdersError,
      topShareholders: topShareholders, filteredTopShareholders: filteredTopShareholders,
      shareholderSearchQuery: shareholderSearchQuery,
      shStockQuery: shStockQuery, shStockResult: shStockResult,
      shStockLoading: shStockLoading, shStockError: shStockError,
      shStockSearched: shStockSearched, searchShareholdersByStock: searchShareholdersByStock,
      shStockList: shStockList, shStockSelected: shStockSelected,
      shStockActiveLabel: shStockActiveLabel, onShStockSelect: onShStockSelect,
      shHolderQuery: shHolderQuery, shHolderResult: shHolderResult,
      shHolderLoading: shHolderLoading, shHolderError: shHolderError,
      shHolderSearched: shHolderSearched,
      searchShareholdersByHolder: searchShareholdersByHolder,
      shHolderActiveName: shHolderActiveName, popularHolders: popularHolders,
      selectHolder: selectHolder,
      // Market Reports
      mrReports: mrReports, mrStats: mrStats, mrAnalysis: mrAnalysis,
      mrLoadingAnalysis: mrLoadingAnalysis, mrFilter: mrFilter, setMrFilter: setMrFilter,
      mrBtData: mrBtData, mrBtLoading: mrBtLoading, mrBtError: mrBtError,
      mrMonths: mrMonths, mrExpandedMonths: mrExpandedMonths, toggleMonth: toggleMonth,
      mrNetForeign: mrNetForeign, mrSortedForeign: mrSortedForeign,
      toggleMrSort: toggleMrSort, mrSortIcon: mrSortIcon,
      loadMrAnalysis: loadMrAnalysis, loadBacktest: loadBacktest,
      loadForeignOverview: loadForeignOverview, loadMarketReports: loadMarketReports,
      // Settings
      settingsLanguage: settingsLanguage, settingsRiskTolerance: settingsRiskTolerance,
      settingsTargetProfit: settingsTargetProfit,
      settingsEmailNotif: settingsEmailNotif, settingsPushNotif: settingsPushNotif,
      settingsAlerts: settingsAlerts, newAlertStock: newAlertStock,
      newAlertType: newAlertType, newAlertCondition: newAlertCondition,
      addAlert: addAlert, removeAlert: removeAlert,
      mockScan: mockScan, mockSave: mockSave,
      // Formatters
      formatRp: formatRp, formatVolume: formatVolume, formatPrice: formatPrice,
      // Watchlist
      watchlist: watchlist,
      // Loading States
      overviewLoading: overviewLoading, daytradingLoading: daytradingLoading,
      longtermLoading: longtermLoading, analysisLoading: analysisLoading,
      shareholdersLoading: shareholdersLoading, mrReportsLoading: mrReportsLoading,
    };
  }
}).mount('#app');
