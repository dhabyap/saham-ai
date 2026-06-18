const { createApp, ref, computed, onMounted } = Vue;

createApp({
  setup() {
    // ── State ──
    const currentTheme = ref('dark');
    const themes = ['light', 'dark', 'blue', 'gold'];
    const headerTitle = ref('SahamAI — Intelligent Market Analysis');
    const currentView = ref('dashboard');
    const navItems = [
      { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
      { id: 'daytrading', label: 'Day Trading', icon: '⚡' },
      { id: 'longterm', label: 'Long Term', icon: '💎' },
      { id: 'analysis', label: 'Analysis', icon: '🔍' },
      { id: 'shareholders', label: 'Shareholders', icon: '👥' },
      { id: 'marketreports', label: 'Reports', icon: '📜' },
    ];
    const currentTab = ref('signals');
    const searchQuery = ref('');
    const searchOpen = ref(false);
    const sidebarOpen = ref(true);
    const dateStr = ref('');
    
    // ── Loaders / API Data ──
    const overviewLoading = ref(true);
    const stocksLoading = ref(false);
    const daytradingLoading = ref(true);
    const longtermLoading = ref(true);
    const analysisLoading = ref(true);
    const shareholdersLoading = ref(true);
    const mrReportsLoading = ref(true);
    
    const foreignOverviewStocks = ref([]);
    const pahlawanBursaStocks = ref([]);
    const dailyNetTotal = ref(0);
    const foreignStockCount = ref(0);
    const foreignActivitySummary = ref('');
    const market = ref([]);
    const aiPerf = ref([]);
    const aiPerfDetails = ref([]);
    const movers = ref([]);
    const allGainers = ref([]);
    const allLosers = ref([]);
    const allVolume = ref([]);
    const bpjsSignals = ref([]);
    const longTermSignals = ref([]);
    const sectors = ref([]);
    const predictions = ref([]);
    const allPredictions = ref([]);
    
    const dayTradingSignals = ref([]);
    const dayTradingCandidates = ref([]);
    const dayTradingHistory = ref([]);
    
    const ltAccumulation = ref([]);
    const ltPortfolio = ref([]);
    const ltWatchlist = ref([]);
    
    const analysisQuery = ref('');
    const analysisSector = ref('All');
    const analysisSectors = ref(['All', 'Finance', 'Consumer', 'Energy', 'Mining', 'Industrial', 'Health', 'Tech']);
    const analysisStocks = ref([]);
    const filteredAnalysis = computed(() => {
      if (analysisQuery.value === '') return analysisStocks.value;
      return analysisStocks.value.filter(s => s.code.toLowerCase().includes(analysisQuery.value.toLowerCase()));
    });
    const selectedStock = ref(null);
    
    const shareholdersStats = ref({ total_records: 0, total_stocks: 0, total_holders: 0, top_holder: '' });
    const shareholdersLatestPeriod = ref('');
    const topShareholders = ref([]);
    
    const mrReports = ref([]);
    const mrStats = ref([]);
    const mrAnalysis = ref([]);
    const mrLoadingAnalysis = ref(false);
    const mrFilter = ref('All');
    const mrBtData = ref([]);
    const mrBtLoading = ref(false);
    const mrBtError = ref(null);
    const mrMonths = ref([]);
    const mrExpandedMonths = ref([]);
    
    const settingsLanguage = ref('ID');
    const settingsRiskTolerance = ref('Medium');
    const settingsTargetProfit = ref('10%');
    const settingsEmailNotif = ref(true);
    const settingsPushNotif = ref(true);
    const settingsAlerts = ref([]);
    const newAlertStock = ref('');
    const newAlertType = ref('Price');
    const newAlertCondition = ref('');
    
    const watchlist = ref([]);

    // ── UI Logic ──
    const switchView = (view) => {
      currentView.value = view;
      if (view === 'daytrading') currentTab.value = 'signals';
      if (view === 'longterm') currentTab.value = 'accumulation';
      if (view === 'analysis') currentTab.value = 'search';
      if (view === 'shareholders') currentTab.value = 'overview';
      if (view === 'marketreports') currentTab.value = 'overview';
    };
    const switchTab = (tab) => {
      currentTab.value = tab;
    };
    const toggleSidebar = () => {
      sidebarOpen.value = !sidebarOpen.value;
    };
    const openSearch = () => {
      searchOpen.value = true;
      searchQuery.value = '';
    };
    const closeSearch = () => {
      searchOpen.value = false;
    };
    const onSearchInput = () => {
      if (searchQuery.value.length > 2) {
        searchOpen.value = false;
        // logic filter stocks
      }
    };

    // ── Init ──
    onMounted(() => {
      var d = new Date();
      dateStr.value = d.toLocaleDateString('en-ID', { month: 'short', day: 'numeric', year: 'numeric' });
      document.addEventListener('keydown', function(e) { if (e.key === 'Escape') searchOpen.value = false; });
      syncViewFromUrl();
      loadForeignOverview();
      window.addEventListener('hashchange', function() { syncViewFromUrl(); });
      loadAllData();
      loadAllDashboardData();
      startAutoRefresh();
    });

    return {
      // Appearance
      currentTheme: currentTheme, themes: themes, headerTitle: headerTitle,
      // Navigation
      currentView: currentView, navItems: navItems, currentTab: currentTab,
      switchView: switchView, switchTab: switchTab,
      // Search / Sidebar
      searchQuery: searchQuery, searchOpen: searchOpen, sidebarOpen: sidebarOpen,
      filteredStocks: filteredStocks, allStocks: allStocks,
      toggleSidebar: toggleSidebar, openSearch: openSearch, closeSearch: closeSearch, onSearchInput: onSearchInput,
      dateStr: dateStr,
      // Dashboard Overview
      overviewLoading: overviewLoading,
      daytradingLoading: daytradingLoading,
      longtermLoading: longtermLoading,
      analysisLoading: analysisLoading,
      shareholdersLoading: shareholdersLoading,
      mrReportsLoading: mrReportsLoading,
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
    };
  }
}).mount('#app');
