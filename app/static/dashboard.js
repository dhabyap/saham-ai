    const { createApp, ref, computed, onMounted, watch } = Vue;

    createApp({
      setup() {
        const currentTheme = ref('neumorphism');
        const currentView = ref('dashboard');
        const currentTab = ref('overview');
        const searchQuery = ref('');
        const sidebarOpen = ref(true);
        const searchOpen = ref(false);
        const dateStr = ref('');
        const mrReports = ref([]);
        const mrStats = ref({ totalReports: 0, avgIHSG: 0, foreignStocks: 0, redDays: 0 });
        const mrForeignStocks = ref([]);
        const mrLocalStocks = ref([]);
        const mrAnalysis = ref(null);
        const mrLoadingAnalysis = ref(false);
        const mrExpandedMonths = ref({});
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
        let ihsgChartInstance = null;
        let foreignChartInstance = null;

        const themes = [
          { id: 'neumorphism', label: 'Light' },
          { id: 'dark', label: 'Dark' },
          { id: 'classy', label: 'Classy' },
        ];

        const navItems = [
          { view: 'dashboard',  icon: '&#9751;', label: 'Dashboard' },
          { view: 'daytrading', icon: '&#8644;', label: 'Day Trading' },
          { view: 'longterm',   icon: '&#9670;', label: 'Long Term' },
          { view: 'analysis',   icon: '&#9776;', label: 'Analysis' },
          { view: 'settings',   icon: '&#9881;', label: 'Settings' },
          { view: 'marketreports', icon: '📊', label: 'Market Reports' },
        ];

        const headerTitle = computed(() => {
          const map = { dashboard: 'Dashboard', daytrading: 'Day Trading', longterm: 'Long Term', analysis: 'Analysis', settings: 'Settings', marketreports: 'Market Reports' };
          return map[currentView.value] || 'Dashboard';
        });

        const dashboardTabs = [
          { id: 'overview', label: 'Overview' },
          { id: 'aiperf', label: 'AI Performance' },
          { id: 'movers', label: 'Market Movers' },
          { id: 'sectors', label: 'Sectors' },
          { id: 'preds', label: 'Predictions' },
        ];
        const daytradingTabs = [
          { id: 'signals', label: 'Signals' },
          { id: 'candidates', label: 'Candidates' },
          { id: 'history', label: 'History' },
        ];
        const longtermTabs = [
          { id: 'accumulation', label: 'Accumulation' },
          { id: 'portfolio', label: 'Portfolio' },
          { id: 'watchlist', label: 'Watchlist' },
        ];
        const analysisTabs = [
          { id: 'search', label: 'Search' },
          { id: 'detail', label: 'Detail' },
          { id: 'comparison', label: 'Comparison' },
        ];
        const settingsTabs = [
          { id: 'general', label: 'General' },
          { id: 'account', label: 'Account' },
          { id: 'alerts', label: 'Alerts' },
        ];

        const watchlist = ref([
          { code: 'BBCA', chg: 3.5 },
          { code: 'ASII', chg: 2.8 },
          { code: 'TLKM', chg: -2.1 },
          { code: 'ADRO', chg: 1.4 },
          { code: 'ICBP', chg: 0.2 },
          { code: 'BBRI', chg: 1.9 },
          { code: 'UNVR', chg: -0.8 },
          { code: 'GOTO', chg: -3.2 },
        ]);

        const allStocks = [
          { code: 'BBCA', name: 'Bank Central Asia', chg: 3.5 },
          { code: 'ASII', name: 'Astra International', chg: 2.8 },
          { code: 'TLKM', name: 'Telkom Indonesia', chg: -2.1 },
          { code: 'ADRO', name: 'Adaro Energy', chg: 1.4 },
          { code: 'ICBP', name: 'Indofood CBP', chg: 0.2 },
          { code: 'BBRI', name: 'Bank Rakyat Indonesia', chg: 1.9 },
          { code: 'UNVR', name: 'Unilever Indonesia', chg: -0.8 },
          { code: 'GOTO', name: 'GoTo Gojek Tokopedia', chg: -3.2 },
          { code: 'BBNI', name: 'Bank Negara Indonesia', chg: 1.1 },
          { code: 'INDF', name: 'Indofood Sukses Makmur', chg: -0.5 },
        ];

        const filteredStocks = computed(() => {
          const q = searchQuery.value.toLowerCase();
          if (!q) return allStocks;
          return allStocks.filter(s =>
            s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
          );
        });

        const market = ref({
          fgi: { value: 62, label: 'Greed' },
          advancing: { count: 285, change: 185, pct: '52%' },
          declining: { count: 263, change: 263, pct: '48%' },
          avgChange: '+0.38%',
          totalVolume: '12.8B',
          volumeChange: '+8.2% vs prev session',
          status: 'Open',
          hours: '09:00 \u2013 15:00 WIB',
        });

        const aiPerf = ref({
          accuracy: '72.5%',
          accuracyChange: '+2.3% vs prev week',
          winRate: '65.3%',
          winRateChange: '+1.1% vs prev week',
          avgProfit: '+1.8%',
          totalPredictions: '127',
        });

        const aiPerfDetails = ref([
          { metric: 'Accuracy (30d)', value: '71.2%', trend: '+1.8%', trendClass: 'profit-positive', desc: 'Overall prediction accuracy over 30 days' },
          { metric: 'Win Rate (30d)', value: '64.7%', trend: '+0.9%', trendClass: 'profit-positive', desc: 'Percentage of profitable trades' },
          { metric: 'Avg Hold Time', value: '2.4 days', trend: '-0.3d', trendClass: 'profit-positive', desc: 'Average position holding period' },
          { metric: 'Max Drawdown', value: '-4.2%', trend: '-1.1%', trendClass: 'profit-positive', desc: 'Maximum portfolio drawdown' },
          { metric: 'Sharpe Ratio', value: '1.84', trend: '+0.12', trendClass: 'profit-positive', desc: 'Risk-adjusted return metric' },
          { metric: 'Profit Factor', value: '2.31', trend: '+0.18', trendClass: 'profit-positive', desc: 'Gross profit / gross loss' },
          { metric: 'Best Trade', value: 'BBCA +8.2%', trend: '-', trendClass: '', desc: 'Highest profit single trade' },
          { metric: 'Worst Trade', value: 'GOTO -4.1%', trend: '-', trendClass: '', desc: 'Highest loss single trade' },
        ]);

        const movers = ref({
          gainers: [
            { code: 'BBCA', name: 'Bank Central Asia', chg: '+3.5%' },
            { code: 'ASII', name: 'Astra International', chg: '+2.8%' },
            { code: 'ADRO', name: 'Adaro Energy', chg: '+2.1%' },
          ],
          losers: [
            { code: 'TLKM', name: 'Telkom Indonesia', chg: '-2.1%' },
            { code: 'GOTO', name: 'GoTo Gojek Tokopedia', chg: '-3.2%' },
            { code: 'UNVR', name: 'Unilever Indonesia', chg: '-0.8%' },
          ],
          volume: [
            { code: 'BBRI', name: 'Bank Rakyat Indonesia', vol: '218.3M' },
            { code: 'GOTO', name: 'GoTo Gojek Tokopedia', vol: '187.6M' },
            { code: 'BBCA', name: 'Bank Central Asia', vol: '142.1M' },
          ],
        });

        const allGainers = ref([
          { code: 'BBCA', name: 'Bank Central Asia', chg: '+3.5%' },
          { code: 'ASII', name: 'Astra International', chg: '+2.8%' },
          { code: 'ADRO', name: 'Adaro Energy', chg: '+2.1%' },
          { code: 'BBRI', name: 'Bank Rakyat Indonesia', chg: '+1.9%' },
          { code: 'ICBP', name: 'Indofood CBP', chg: '+1.2%' },
          { code: 'BBNI', name: 'Bank Negara Indonesia', chg: '+1.1%' },
        ]);

        const allLosers = ref([
          { code: 'GOTO', name: 'GoTo Gojek Tokopedia', chg: '-3.2%' },
          { code: 'TLKM', name: 'Telkom Indonesia', chg: '-2.1%' },
          { code: 'UNVR', name: 'Unilever Indonesia', chg: '-0.8%' },
          { code: 'INDF', name: 'Indofood Sukses Makmur', chg: '-0.5%' },
          { code: 'SMGR', name: 'Semen Indonesia', chg: '-0.3%' },
        ]);

        const allVolume = ref([
          { code: 'BBRI', name: 'Bank Rakyat Indonesia', vol: '218.3M' },
          { code: 'GOTO', name: 'GoTo Gojek Tokopedia', vol: '187.6M' },
          { code: 'BBCA', name: 'Bank Central Asia', vol: '142.1M' },
          { code: 'ASII', name: 'Astra International', vol: '98.7M' },
          { code: 'TLKM', name: 'Telkom Indonesia', vol: '76.4M' },
        ]);

        const bpjsSignals = ref([
          { code: 'BBCA', signal: 'ENTER', signalClass: 'success', confidence: 87, price: 'Rp 9,850' },
          { code: 'ASII', signal: 'ENTER', signalClass: 'success', confidence: 82, price: 'Rp 5,600' },
          { code: 'ADRO', signal: 'WAIT', signalClass: 'warning', confidence: 64, price: 'Rp 2,890' },
          { code: 'BBRI', signal: 'ENTER', signalClass: 'success', confidence: 79, price: 'Rp 4,420' },
        ]);

        const longTermSignals = ref([
          { code: 'ICBP', signal: 'Active Accum', signalClass: 'accent', confidence: 91, entryZone: 'Rp 10,200 \u2013 10,600' },
          { code: 'UNVR', signal: 'Accum Watch', signalClass: 'warning', confidence: 73, entryZone: 'Rp 2,800 \u2013 3,100' },
          { code: 'TLKM', signal: 'Active Accum', signalClass: 'accent', confidence: 85, entryZone: 'Rp 3,600 \u2013 3,900' },
          { code: 'GOTO', signal: 'Avoid', signalClass: 'danger', confidence: 42, entryZone: 'N/A' },
        ]);

        const sectors = ref([
          { name: 'Technology', width: '76%', barColor: 'var(--success)', textColor: 'var(--success)', change: '+2.31%', flow: 'Inflow', flowClass: 'success' },
          { name: 'Financials', width: '62%', barColor: 'var(--success)', textColor: 'var(--success)', change: '+1.87%', flow: 'Inflow', flowClass: 'success' },
          { name: 'Energy', width: '48%', barColor: 'var(--accent)', textColor: 'var(--accent)', change: '+0.95%', flow: 'Neutral', flowClass: 'accent' },
          { name: 'Consumer Cycl.', width: '28%', barColor: 'var(--warning)', textColor: 'var(--warning)', change: '-0.42%', flow: 'Neutral', flowClass: 'warning' },
          { name: 'Healthcare', width: '18%', barColor: 'var(--danger)', textColor: 'var(--danger)', change: '-1.23%', flow: 'Outflow', flowClass: 'danger' },
          { name: 'Infrastructure', width: '12%', barColor: 'var(--danger)', textColor: 'var(--danger)', change: '-2.05%', flow: 'Outflow', flowClass: 'danger' },
        ]);

        const predictions = ref([
          { code: 'BBCA', signal: 'BUY', signalClass: 'success', confidence: 87, result: 'Win', resultClass: 'success', profit: '+3.5%', profitClass: 'profit-positive', date: 'Jun 04' },
          { code: 'TLKM', signal: 'SELL', signalClass: 'danger', confidence: 76, result: 'Win', resultClass: 'success', profit: '+2.1%', profitClass: 'profit-positive', date: 'Jun 03' },
          { code: 'ASII', signal: 'BUY', signalClass: 'success', confidence: 82, result: 'Win', resultClass: 'success', profit: '+2.8%', profitClass: 'profit-positive', date: 'Jun 03' },
          { code: 'GOTO', signal: 'BUY', signalClass: 'success', confidence: 68, result: 'Loss', resultClass: 'danger', profit: '-1.4%', profitClass: 'profit-negative', date: 'Jun 02' },
          { code: 'ADRO', signal: 'HOLD', signalClass: 'warning', confidence: 55, result: 'Pending', resultClass: 'warning', profit: '+0.2%', profitClass: 'profit-positive', date: 'Jun 02' },
        ]);

        const allPredictions = ref([
          { code: 'BBCA', signal: 'BUY', signalClass: 'success', confidence: 87, result: 'Win', resultClass: 'success', profit: '+3.5%', profitClass: 'profit-positive', date: 'Jun 04' },
          { code: 'TLKM', signal: 'SELL', signalClass: 'danger', confidence: 76, result: 'Win', resultClass: 'success', profit: '+2.1%', profitClass: 'profit-positive', date: 'Jun 03' },
          { code: 'ASII', signal: 'BUY', signalClass: 'success', confidence: 82, result: 'Win', resultClass: 'success', profit: '+2.8%', profitClass: 'profit-positive', date: 'Jun 03' },
          { code: 'GOTO', signal: 'BUY', signalClass: 'success', confidence: 68, result: 'Loss', resultClass: 'danger', profit: '-1.4%', profitClass: 'profit-negative', date: 'Jun 02' },
          { code: 'ADRO', signal: 'HOLD', signalClass: 'warning', confidence: 55, result: 'Pending', resultClass: 'warning', profit: '+0.2%', profitClass: 'profit-positive', date: 'Jun 02' },
          { code: 'BBRI', signal: 'BUY', signalClass: 'success', confidence: 79, result: 'Win', resultClass: 'success', profit: '+1.9%', profitClass: 'profit-positive', date: 'Jun 01' },
          { code: 'ICBP', signal: 'HOLD', signalClass: 'warning', confidence: 63, result: 'Pending', resultClass: 'warning', profit: '+0.5%', profitClass: 'profit-positive', date: 'May 31' },
          { code: 'UNVR', signal: 'SELL', signalClass: 'danger', confidence: 71, result: 'Win', resultClass: 'success', profit: '+1.8%', profitClass: 'profit-positive', date: 'May 30' },
        ]);

        const dayTradingSignals = ref([
          { code: 'BBCA', signal: 'ENTER', signalClass: 'success', confidence: 87, price: 'Rp 9,850', entry: 'Rp 9,800', exit: 'Rp 10,200' },
          { code: 'ASII', signal: 'ENTER', signalClass: 'success', confidence: 82, price: 'Rp 5,600', entry: 'Rp 5,550', exit: 'Rp 5,900' },
          { code: 'ADRO', signal: 'WAIT', signalClass: 'warning', confidence: 64, price: 'Rp 2,890', entry: 'Rp 2,850', exit: 'Rp 3,050' },
          { code: 'BBRI', signal: 'ENTER', signalClass: 'success', confidence: 79, price: 'Rp 4,420', entry: 'Rp 4,380', exit: 'Rp 4,650' },
          { code: 'TLKM', signal: 'WAIT', signalClass: 'warning', confidence: 58, price: 'Rp 3,210', entry: 'Rp 3,150', exit: 'Rp 3,400' },
          { code: 'GOTO', signal: 'ENTER', signalClass: 'success', confidence: 71, price: 'Rp 1,850', entry: 'Rp 1,820', exit: 'Rp 1,980' },
          { code: 'UNVR', signal: 'WAIT', signalClass: 'warning', confidence: 52, price: 'Rp 2,950', entry: 'Rp 2,900', exit: 'Rp 3,100' },
          { code: 'ICBP', signal: 'ENTER', signalClass: 'success', confidence: 76, price: 'Rp 10,400', entry: 'Rp 10,300', exit: 'Rp 10,900' },
        ]);

        const dayTradingCandidates = ref([
          { stock: 'BBCA', signal: 'ENTER', signalClass: 'success', conf: 87, entry: '9,800', tp: '10,200', cl: '9,650', volRatio: '2.3x', foreignFlow: '+1.2B', action: 'Buy' },
          { stock: 'ASII', signal: 'ENTER', signalClass: 'success', conf: 82, entry: '5,550', tp: '5,900', cl: '5,450', volRatio: '1.8x', foreignFlow: '+0.8B', action: 'Buy' },
          { stock: 'BBRI', signal: 'ENTER', signalClass: 'success', conf: 79, entry: '4,380', tp: '4,650', cl: '4,300', volRatio: '1.5x', foreignFlow: '+0.6B', action: 'Buy' },
          { stock: 'ICBP', signal: 'ENTER', signalClass: 'success', conf: 76, entry: '10,300', tp: '10,900', cl: '10,100', volRatio: '2.1x', foreignFlow: '+0.4B', action: 'Buy' },
          { stock: 'BBNI', signal: 'ENTER', signalClass: 'success', conf: 74, entry: '5,100', tp: '5,400', cl: '5,000', volRatio: '1.6x', foreignFlow: '+0.5B', action: 'Buy' },
          { stock: 'GOTO', signal: 'ENTER', signalClass: 'success', conf: 71, entry: '1,820', tp: '1,980', cl: '1,750', volRatio: '1.4x', foreignFlow: '+0.3B', action: 'Buy' },
          { stock: 'ADRO', signal: 'WAIT', signalClass: 'warning', conf: 64, entry: '2,850', tp: '3,050', cl: '2,780', volRatio: '0.9x', foreignFlow: '-0.1B', action: 'Watch' },
          { stock: 'INDF', signal: 'WAIT', signalClass: 'warning', conf: 61, entry: '6,800', tp: '7,200', cl: '6,650', volRatio: '0.8x', foreignFlow: '+0.1B', action: 'Watch' },
          { stock: 'TLKM', signal: 'WAIT', signalClass: 'warning', conf: 58, entry: '3,150', tp: '3,400', cl: '3,080', volRatio: '0.7x', foreignFlow: '-0.2B', action: 'Watch' },
          { stock: 'UNVR', signal: 'WAIT', signalClass: 'warning', conf: 52, entry: '2,900', tp: '3,100', cl: '2,850', volRatio: '0.6x', foreignFlow: '-0.1B', action: 'Watch' },
        ]);

        const dayTradingHistory = ref([
          { date: 'Jun 04', stock: 'BBCA', entry: '9,750', exit: '10,100', profit: '+3.6%', profitClass: 'profit-positive', result: 'Win', resultClass: 'success' },
          { date: 'Jun 03', stock: 'ASII', entry: '5,500', exit: '5,800', profit: '+5.5%', profitClass: 'profit-positive', result: 'Win', resultClass: 'success' },
          { date: 'Jun 03', stock: 'BBRI', entry: '4,400', exit: '4,500', profit: '+2.3%', profitClass: 'profit-positive', result: 'Win', resultClass: 'success' },
          { date: 'Jun 02', stock: 'GOTO', entry: '1,900', exit: '1,860', profit: '-2.1%', profitClass: 'profit-negative', result: 'Loss', resultClass: 'danger' },
          { date: 'Jun 02', stock: 'ADRO', entry: '2,900', exit: '2,950', profit: '+1.7%', profitClass: 'profit-positive', result: 'Win', resultClass: 'success' },
          { date: 'Jun 01', stock: 'TLKM', entry: '3,200', exit: '3,150', profit: '-1.6%', profitClass: 'profit-negative', result: 'Loss', resultClass: 'danger' },
          { date: 'Jun 01', stock: 'ICBP', entry: '10,250', exit: '10,500', profit: '+2.4%', profitClass: 'profit-positive', result: 'Win', resultClass: 'success' },
          { date: 'May 31', stock: 'UNVR', entry: '3,000', exit: '2,950', profit: '-1.7%', profitClass: 'profit-negative', result: 'Pending', resultClass: 'warning' },
        ]);

        const ltAccumulation = ref([
          { code: 'ICBP', phase: 'Active Accum', signalClass: 'accent', confidence: 91, entryZone: '10,200 \u2013 10,600', accumDays: 24, rsStatus: 'Strong' },
          { code: 'TLKM', phase: 'Active Accum', signalClass: 'accent', confidence: 85, entryZone: '3,600 \u2013 3,900', accumDays: 18, rsStatus: 'Strong' },
          { code: 'ASII', phase: 'Early Accum', signalClass: 'accent', confidence: 78, entryZone: '5,400 \u2013 5,700', accumDays: 8, rsStatus: 'Improving' },
          { code: 'BBRI', phase: 'Accum Watch', signalClass: 'warning', confidence: 73, entryZone: '4,200 \u2013 4,500', accumDays: 12, rsStatus: 'Neutral' },
          { code: 'UNVR', phase: 'Accum Watch', signalClass: 'warning', confidence: 68, entryZone: '2,800 \u2013 3,100', accumDays: 6, rsStatus: 'Neutral' },
          { code: 'BBCA', phase: 'Distribution', signalClass: 'danger', confidence: 55, entryZone: 'N/A', accumDays: 0, rsStatus: 'Weak' },
          { code: 'ADRO', phase: 'Accum Watch', signalClass: 'warning', confidence: 62, entryZone: '2,750 \u2013 2,950', accumDays: 5, rsStatus: 'Improving' },
          { code: 'BBNI', phase: 'Early Accum', signalClass: 'accent', confidence: 71, entryZone: '4,900 \u2013 5,200', accumDays: 10, rsStatus: 'Improving' },
        ]);

        const ltPortfolio = ref([
          { stock: 'ICBP', entryDate: 'May 12', avgPrice: '10,250', currentPrice: '10,400', profitPct: '+1.5%', profitClass: 'profit-positive', position: '1,000', status: 'Holding', statusClass: 'accent' },
          { stock: 'TLKM', entryDate: 'May 18', avgPrice: '3,650', currentPrice: '3,210', profitPct: '-12.1%', profitClass: 'profit-negative', position: '2,500', status: 'Holding', statusClass: 'warning' },
          { stock: 'ASII', entryDate: 'May 25', avgPrice: '5,500', currentPrice: '5,600', profitPct: '+1.8%', profitClass: 'profit-positive', position: '1,500', status: 'Holding', statusClass: 'accent' },
          { stock: 'BBRI', entryDate: 'Jun 01', avgPrice: '4,300', currentPrice: '4,420', profitPct: '+2.8%', profitClass: 'profit-positive', position: '2,000', status: 'Holding', statusClass: 'accent' },
          { stock: 'INDF', entryDate: 'May 05', avgPrice: '6,950', currentPrice: '6,800', profitPct: '-2.2%', profitClass: 'profit-negative', position: '800', status: 'Holding', statusClass: 'warning' },
        ]);

        const ltWatchlist = ref([
          { code: 'BBCA', name: 'Bank Central Asia', chg: 3.5, volume: '142.1M', sector: 'Financials' },
          { code: 'ASII', name: 'Astra International', chg: 2.8, volume: '98.7M', sector: 'Consumer Cycl.' },
          { code: 'TLKM', name: 'Telkom Indonesia', chg: -2.1, volume: '76.4M', sector: 'Technology' },
          { code: 'ADRO', name: 'Adaro Energy', chg: 1.4, volume: '52.3M', sector: 'Energy' },
          { code: 'ICBP', name: 'Indofood CBP', chg: 0.2, volume: '28.1M', sector: 'Consumer Cycl.' },
          { code: 'BBRI', name: 'Bank Rakyat Indonesia', chg: 1.9, volume: '218.3M', sector: 'Financials' },
          { code: 'UNVR', name: 'Unilever Indonesia', chg: -0.8, volume: '22.6M', sector: 'Consumer Cycl.' },
          { code: 'GOTO', name: 'GoTo Gojek Tokopedia', chg: -3.2, volume: '187.6M', sector: 'Technology' },
        ]);

        const analysisQuery = ref('');
        const analysisSector = ref('All');
        const analysisSectors = ['All', 'Financials', 'Technology', 'Energy', 'Consumer Cycl.', 'Healthcare'];

        const analysisStocks = ref([
          { code: 'BBCA', name: 'Bank Central Asia', chg: 3.5, sector: 'Financials', price: 'Rp 9,850', score: 87 },
          { code: 'ASII', name: 'Astra International', chg: 2.8, sector: 'Consumer Cycl.', price: 'Rp 5,600', score: 82 },
          { code: 'TLKM', name: 'Telkom Indonesia', chg: -2.1, sector: 'Technology', price: 'Rp 3,210', score: 64 },
          { code: 'ADRO', name: 'Adaro Energy', chg: 1.4, sector: 'Energy', price: 'Rp 2,890', score: 71 },
          { code: 'ICBP', name: 'Indofood CBP', chg: 0.2, sector: 'Consumer Cycl.', price: 'Rp 10,400', score: 78 },
          { code: 'BBRI', name: 'Bank Rakyat Indonesia', chg: 1.9, sector: 'Financials', price: 'Rp 4,420', score: 79 },
          { code: 'UNVR', name: 'Unilever Indonesia', chg: -0.8, sector: 'Consumer Cycl.', price: 'Rp 2,950', score: 52 },
          { code: 'GOTO', name: 'GoTo Gojek Tokopedia', chg: -3.2, sector: 'Technology', price: 'Rp 1,850', score: 42 },
          { code: 'BBNI', name: 'Bank Negara Indonesia', chg: 1.1, sector: 'Financials', price: 'Rp 5,200', score: 74 },
          { code: 'INDF', name: 'Indofood Sukses Makmur', chg: -0.5, sector: 'Consumer Cycl.', price: 'Rp 6,800', score: 61 },
        ]);

        const filteredAnalysis = computed(() => {
          let items = analysisStocks.value;
          if (analysisSector.value !== 'All') {
            items = items.filter(s => s.sector === analysisSector.value);
          }
          if (analysisQuery.value) {
            const q = analysisQuery.value.toLowerCase();
            items = items.filter(s => s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q));
          }
          return items;
        });

        const selectedStock = ref({
          code: 'BBCA',
          name: 'Bank Central Asia',
          price: 'Rp 9,850',
          chg: 1.2,
          rsi: '62.4',
          rsiLabel: 'Neutral-Bullish',
          macd: '+28.5',
          ma20: 'Rp 9,720',
          ma50: 'Rp 9,450',
          bbUpper: 'Rp 10,120',
          bbLower: 'Rp 9,380',
          r2: 'Rp 10,400',
          r1: 'Rp 10,100',
          pivot: 'Rp 9,850',
          s1: 'Rp 9,600',
          s2: 'Rp 9,400',
          volume: '142.1M',
          score: 87,
          confidence: 82,
          recommendation: 'BUY',
          signalClass: 'success',
          analysis: 'BBCA shows strong bullish momentum with RSI at 62.4 indicating room for further upside. MACD positive crossover confirmed. Price above both MA20 and MA50 suggesting sustained uptrend. Volume increasing with strong foreign inflow. Accumulation phase detected with institutional buying pressure. Recommended entry at Rp 9,800 with TP at Rp 10,200 and CL at Rp 9,650.',
        });

        function selectStock(item) {
          const detailMap = {
            BBCA: { rsi: '62.4', rsiLabel: 'Neutral-Bullish', macd: '+28.5', ma20: 'Rp 9,720', ma50: 'Rp 9,450', bbUpper: 'Rp 10,120', bbLower: 'Rp 9,380', r2: 'Rp 10,400', r1: 'Rp 10,100', pivot: 'Rp 9,850', s1: 'Rp 9,600', s2: 'Rp 9,400', volume: '142.1M', score: 87, confidence: 82, recommendation: 'BUY', signalClass: 'success', analysis: 'BBCA shows strong bullish momentum with RSI at 62.4 indicating room for further upside. MACD positive crossover confirmed. Price above both MA20 and MA50 suggesting sustained uptrend. Volume increasing with strong foreign inflow.' },
            ASII: { rsi: '58.2', rsiLabel: 'Neutral', macd: '+12.3', ma20: 'Rp 5,520', ma50: 'Rp 5,380', bbUpper: 'Rp 5,850', bbLower: 'Rp 5,300', r2: 'Rp 5,950', r1: 'Rp 5,780', pivot: 'Rp 5,600', s1: 'Rp 5,420', s2: 'Rp 5,250', volume: '98.7M', score: 82, confidence: 78, recommendation: 'BUY', signalClass: 'success', analysis: 'ASII recovering from consolidation with improving volume. RSI neutral leaving room for upside. MACD showing early positive crossover. Accumulation pattern forming above MA50.' },
            TLKM: { rsi: '38.5', rsiLabel: 'Bearish', macd: '-15.2', ma20: 'Rp 3,350', ma50: 'Rp 3,450', bbUpper: 'Rp 3,600', bbLower: 'Rp 3,100', r2: 'Rp 3,400', r1: 'Rp 3,300', pivot: 'Rp 3,210', s1: 'Rp 3,120', s2: 'Rp 3,030', volume: '76.4M', score: 64, confidence: 58, recommendation: 'WAIT', signalClass: 'warning', analysis: 'TLKM in short-term downtrend. RSI below 40 indicating bearish momentum. Price below both MA20 and MA50. Waiting for reversal confirmation before entry.' },
            ADRO: { rsi: '55.6', rsiLabel: 'Neutral', macd: '+5.8', ma20: 'Rp 2,820', ma50: 'Rp 2,760', bbUpper: 'Rp 3,050', bbLower: 'Rp 2,650', r2: 'Rp 3,050', r1: 'Rp 2,950', pivot: 'Rp 2,890', s1: 'Rp 2,800', s2: 'Rp 2,720', volume: '52.3M', score: 71, confidence: 68, recommendation: 'HOLD', signalClass: 'warning', analysis: 'ADRO showing consolidation near support levels. RSI neutral with no clear direction. Volume declining suggesting lack of catalyst. Wait for breakout above Rp 2,950.' },
          };
          const def = detailMap[item.code] || { rsi: '50.0', rsiLabel: 'Neutral', macd: '0.0', ma20: item.price, ma50: item.price, bbUpper: '-', bbLower: '-', r2: '-', r1: '-', pivot: '-', s1: '-', s2: '-', volume: '-', score: item.score, confidence: Math.round(item.score * 0.9), recommendation: 'HOLD', signalClass: 'warning', analysis: 'Analysis data not available for this stock.' };
          selectedStock.value = { ...item, ...def };
          currentTab.value = 'detail';
        }

        const comparisonStocks = ref([
          { code: 'BBCA', price: '9,850', chg: '+1.2%', rsi: '62.4', macd: '+28.5', volume: '142.1M', score: '87', rec: 'BUY' },
          { code: 'BBRI', price: '4,420', chg: '+1.9%', rsi: '55.8', macd: '+12.1', volume: '218.3M', score: '79', rec: 'HOLD' },
          { code: 'ASII', price: '5,600', chg: '+2.8%', rsi: '58.2', macd: '+8.4', volume: '98.7M', score: '82', rec: 'BUY' },
        ]);

        const comparisonRows = computed(() => [
          { label: 'Price', getValue: s => s.price },
          { label: 'Change %', getValue: s => s.chg, getClass: s => s.chg.startsWith('+') ? 'profit-positive' : 'profit-negative' },
          { label: 'RSI (14)', getValue: s => s.rsi },
          { label: 'MACD', getValue: s => s.macd, getClass: s => s.macd.startsWith('+') ? 'profit-positive' : 'profit-negative' },
          { label: 'Volume', getValue: s => s.volume },
          { label: 'AI Score', getValue: s => s.score, getClass: s => parseInt(s.score) >= 80 ? 'profit-positive' : parseInt(s.score) >= 60 ? '' : 'profit-negative' },
          { label: 'Recommendation', getValue: s => s.rec, getClass: s => s.rec === 'BUY' ? 'profit-positive' : s.rec === 'SELL' ? 'profit-negative' : '' },
        ]);

        const comparisonAddCode = ref('');
        const comparisonAvailable = computed(() => {
          const used = new Set(comparisonStocks.value.map(s => s.code));
          return allStocks.filter(s => !used.has(s.code)).map(s => s.code);
        });

        function addComparison() {
          if (!comparisonAddCode.value) return;
          const stock = allStocks.find(s => s.code === comparisonAddCode.value);
          if (!stock) return;
          const details = {
            BBCA: { price: '9,850', chg: '+1.2%', rsi: '62.4', macd: '+28.5', volume: '142.1M', score: '87', rec: 'BUY' },
            ASII: { price: '5,600', chg: '+2.8%', rsi: '58.2', macd: '+8.4', volume: '98.7M', score: '82', rec: 'BUY' },
            BBRI: { price: '4,420', chg: '+1.9%', rsi: '55.8', macd: '+12.1', volume: '218.3M', score: '79', rec: 'HOLD' },
            TLKM: { price: '3,210', chg: '-2.1%', rsi: '38.5', macd: '-15.2', volume: '76.4M', score: '64', rec: 'WAIT' },
            ADRO: { price: '2,890', chg: '+1.4%', rsi: '55.6', macd: '+5.8', volume: '52.3M', score: '71', rec: 'HOLD' },
            ICBP: { price: '10,400', chg: '+0.2%', rsi: '51.2', macd: '+3.5', volume: '28.1M', score: '78', rec: 'HOLD' },
            UNVR: { price: '2,950', chg: '-0.8%', rsi: '42.1', macd: '-8.2', volume: '22.6M', score: '52', rec: 'SELL' },
            GOTO: { price: '1,850', chg: '-3.2%', rsi: '32.8', macd: '-22.4', volume: '187.6M', score: '42', rec: 'WAIT' },
            BBNI: { price: '5,200', chg: '+1.1%', rsi: '54.3', macd: '+6.7', volume: '45.2M', score: '74', rec: 'HOLD' },
            INDF: { price: '6,800', chg: '-0.5%', rsi: '48.9', macd: '-2.1', volume: '18.5M', score: '61', rec: 'HOLD' },
          };
          const d = details[stock.code] || { price: '-', chg: '0%', rsi: '50', macd: '0', volume: '-', score: '50', rec: 'HOLD' };
          comparisonStocks.value.push({ code: stock.code, ...d });
          comparisonAddCode.value = '';
        }

        const settingsLanguage = ref('en');
        const settingsRiskTolerance = ref('medium');
        const settingsTargetProfit = ref('5');
        const settingsEmailNotif = ref(true);
        const settingsPushNotif = ref(true);

        const settingsAlerts = ref([
          { stock: 'BBCA', type: 'Price Alert', condition: 'Above 10,000', status: 'Active' },
          { stock: 'ASII', type: 'RSI Alert', condition: 'RSI < 30', status: 'Active' },
          { stock: 'TLKM', type: 'Volume Alert', condition: 'Volume > 2x avg', status: 'Active' },
          { stock: 'ICBP', type: 'Price Alert', condition: 'Below 9,800', status: 'Inactive' },
        ]);

        const newAlertStock = ref('');
        const newAlertType = ref('Price Alert');
        const newAlertCondition = ref('');

        function addAlert() {
          if (!newAlertStock.value || !newAlertCondition.value) return;
          settingsAlerts.value.push({
            stock: newAlertStock.value,
            type: newAlertType.value,
            condition: newAlertCondition.value,
            status: 'Active'
          });
          newAlertStock.value = '';
          newAlertType.value = 'Price Alert';
          newAlertCondition.value = '';
        }

        function removeAlert(alert) {
          const idx = settingsAlerts.value.indexOf(alert);
          if (idx > -1) settingsAlerts.value.splice(idx, 1);
        }

        function formatRp(val) {
          if (val >= 1e12) return 'Rp' + (val/1e12).toFixed(2) + 'T';
          if (val >= 1e9) return 'Rp' + (val/1e9).toFixed(1) + 'M';
          if (val >= 1e6) return 'Rp' + (val/1e6).toFixed(1) + 'Jt';
          return 'Rp' + val.toLocaleString('id');
        }

        function renderMrCharts(full) {
          const sorted = [...full].reverse();
          const labels = sorted.map(r => r.date);
          const ihsgData = sorted.map(r => r.ihsg_change);
          const colors = ihsgData.map(v => v >= 0 ? '#10B981' : '#EF5350');

          if (ihsgChartInstance) ihsgChartInstance.destroy();
          const ctx1 = document.getElementById('ihsgChart');
          if (ctx1) {
            ihsgChartInstance = new Chart(ctx1, {
              type: 'bar',
              data: { labels, datasets: [{ label: 'IHSG Change %', data: ihsgData, backgroundColor: colors, borderRadius: 4 }] },
              options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#333' }, ticks: { callback: v => v + '%' } }, x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } } } }
            });
          }

          const fMap = {};
          full.forEach(r => (r.foreign_buy || []).forEach(s => {
            if (!fMap[s.stock]) fMap[s.stock] = { count: 0, total: 0 };
            fMap[s.stock].count++;
            fMap[s.stock].total += s.value;
          }));
          const fSorted = Object.entries(fMap).sort((a,b) => b[1].total - a[1].total).slice(0, 10);

          if (foreignChartInstance) foreignChartInstance.destroy();
          const ctx2 = document.getElementById('foreignChart');
          if (ctx2) {
            foreignChartInstance = new Chart(ctx2, {
              type: 'bar',
              data: { labels: fSorted.map(([k]) => k), datasets: [{ label: 'Foreign Buy (Rp)', data: fSorted.map(([,v]) => v.total), backgroundColor: '#7C3AED', borderRadius: 4 }] },
              options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#333' }, ticks: { callback: v => formatRp(v) } }, x: { grid: { display: false } } } }
            });
          }
        }

        function buildMrStockTable(dataKey, color) {
          const map = {};
          mrReports.value.forEach(r => (r[dataKey] || []).forEach(s => {
            if (!map[s.stock]) map[s.stock] = { count: 0, total: 0, lastDate: r.date };
            map[s.stock].count++;
            map[s.stock].total += s.value;
            if (r.date > map[s.stock].lastDate) map[s.stock].lastDate = r.date;
          }));
          return Object.entries(map).sort((a,b) => b[1].total - a[1].total).map(([k,v]) => ({ stock: k, ...v }));
        }

        async function loadMarketReports() {
          try {
            const res = await fetch('/api/market-reports?limit=500');
            const json = await res.json();
            const full = (json.data || []).filter(r => r.type === 'full');
            mrReports.value = full;

            // Auto-expand first month
            if (full.length) {
              const firstMonth = full[0].date.substring(0, 7);
              mrExpandedMonths.value[firstMonth] = true;
            }

            // Stats
            const ihsgVals = full.map(r => r.ihsg_change).filter(v => v !== null);
            const avgIHSG = ihsgVals.length ? (ihsgVals.reduce((a,b) => a+b, 0) / ihsgVals.length) : 0;
            const allForeignStocks = new Set();
            (json.data || []).forEach(r => (r.foreign_buy || []).forEach(s => allForeignStocks.add(s.stock)));
            const redDays = ihsgVals.filter(v => v < 0).length;
            mrStats.value = { totalReports: json.total || full.length, avgIHSG: Math.round(avgIHSG * 10) / 10, foreignStocks: allForeignStocks.size, redDays };

            // Stock tables
            mrForeignStocks.value = buildMrStockTable('foreign_buy', '#7C3AED');
            mrLocalStocks.value = buildMrStockTable('local_buy', '#06D9FF');

            // Charts
            setTimeout(() => renderMrCharts(full), 100);
          } catch(e) {
            console.error('Market report load failed:', e);
          }
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

        function switchMrTab(tab) {
          currentTab.value = tab;
          if (tab === 'overview') setTimeout(() => renderMrCharts(mrReports.value), 100);
          if (tab === 'analysis' && !mrAnalysis.value) loadMrAnalysis();
        }

        function switchView(view, tab) {
          currentView.value = view;
          if (view === 'marketreports') loadMarketReports();
          const firstTabs = {
            dashboard: 'overview',
            daytrading: 'signals',
            longterm: 'accumulation',
            analysis: 'search',
            settings: 'general',
            marketreports: 'overview',
          };
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

        function mockScan() {
          alert('Scan initiated... Found 8 active signals.');
        }

        function mockSave() {
          alert('Settings saved successfully!');
        }

        watch(currentTheme, (val) => {
          localStorage.setItem('dashboard-theme', val);
          document.documentElement.setAttribute('data-theme', val);
        });

        let _viewChanging = false;

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

        function navigateFromHash() {
          const hash = window.location.hash.replace('#', '');
          if (!hash) return null;
          const parts = hash.split('/');
          const validViews = ['dashboard', 'daytrading', 'longterm', 'analysis', 'settings', 'marketreports'];
          const view = validViews.includes(parts[0]) ? parts[0] : null;
          const tab = parts[1] || null;
          return { view, tab };
        }

        function getViewFromUrl() {
          // Priority 1: URL hash (SPA navigation)
          const fromHash = navigateFromHash();
          if (fromHash && fromHash.view) return fromHash;
          // Priority 2: URL pathname (direct server route)
          const path = window.location.pathname.replace(/\/$/, '');
          const pathMap = { '/market-reports': 'marketreports', '/dashboard': 'dashboard', '/daytrading': 'daytrading', '/longterm': 'longterm', '/analysis': 'analysis', '/settings': 'settings' };
          if (pathMap[path]) return { view: pathMap[path], tab: null };
          // Priority 3: Query param (legacy fallback)
          const params = new URLSearchParams(window.location.search);
          const view = params.get('view');
          const validViews = ['dashboard', 'daytrading', 'longterm', 'analysis', 'settings', 'marketreports'];
          if (validViews.includes(view)) return { view, tab: null };
          return null;
        }

        function syncViewFromUrl() {
          const result = getViewFromUrl();
          if (result && result.view) {
            currentView.value = result.view;
            const firstTabs = {
              dashboard: 'overview', daytrading: 'signals', longterm: 'accumulation',
              analysis: 'search', settings: 'general', marketreports: 'overview',
            };
            _viewChanging = true;
            currentTab.value = result.tab || firstTabs[result.view] || 'overview';
            if (result.view === 'marketreports') loadMarketReports();
          }
        }

        onMounted(() => {
          const saved = localStorage.getItem('dashboard-theme');
          if (saved) {
            currentTheme.value = saved;
          }
          document.documentElement.setAttribute('data-theme', currentTheme.value);
          const d = new Date();
          dateStr.value = d.toLocaleDateString('en-ID', { month: 'short', day: 'numeric', year: 'numeric' });
          document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') searchOpen.value = false;
          });
          // Restore view from URL on initial load
          syncViewFromUrl();
          // Listen for hash changes (browser back/forward)
          window.addEventListener('hashchange', () => {
            const prevView = currentView.value;
            const prevTab = currentTab.value;
            syncViewFromUrl();
          });
        });

        return {
          currentTheme, currentView, currentTab, searchQuery, sidebarOpen, searchOpen, dateStr,
          themes, navItems, headerTitle,
          dashboardTabs, daytradingTabs, longtermTabs, analysisTabs, settingsTabs,
          watchlist, allStocks, filteredStocks,
          market, aiPerf, aiPerfDetails, movers,
          allGainers, allLosers, allVolume,
          bpjsSignals, longTermSignals, sectors, predictions, allPredictions,
          dayTradingSignals, dayTradingCandidates, dayTradingHistory,
          ltAccumulation, ltPortfolio, ltWatchlist,
          analysisQuery, analysisSector, analysisSectors, analysisStocks, filteredAnalysis,
          selectedStock, selectStock,
          comparisonStocks, comparisonRows, comparisonAddCode, comparisonAvailable, addComparison,
          settingsLanguage, settingsRiskTolerance, settingsTargetProfit,
          settingsEmailNotif, settingsPushNotif,
          settingsAlerts, newAlertStock, newAlertType, newAlertCondition, addAlert, removeAlert,
          switchView, switchTheme, toggleSidebar, closeSearch, onSearchInput,
          mockScan, mockSave,
          mrReports, mrStats, mrForeignStocks, mrLocalStocks,
          mrAnalysis, mrLoadingAnalysis,
          mrMonths, mrExpandedMonths, toggleMonth,
          mrNetForeign,
          formatRp, loadMarketReports, loadMrAnalysis, switchMrTab,
        };
      }
    }).mount('#app');
