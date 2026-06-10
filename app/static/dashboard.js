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
          { id: 'treemap', label: 'Heatmap' },
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

        const watchlist = ref([]);
        const allStocks = ref([]);

        const filteredStocks = computed(() => {
          const q = searchQuery.value.toLowerCase();
          if (!q) return allStocks.value;
          return allStocks.value.filter(s =>
            s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
          );
        });

        const market = ref({
          fgi: { value: 50, label: 'Neutral' },
          advancing: { count: 0, change: 0, pct: '0%' },
          declining: { count: 0, change: 0, pct: '0%' },
          avgChange: '0%',
          totalVolume: '0',
          volumeChange: '-',
          status: 'Loading...',
          hours: '-',
        });

        const aiPerf = ref({
          accuracy: '-',
          accuracyChange: '-',
          winRate: '-',
          winRateChange: '-',
          avgProfit: '-',
          totalPredictions: '-',
        });

        const aiPerfDetails = ref([]);

        const movers = ref({ gainers: [], losers: [], volume: [] });
        const allGainers = ref([]);
        const allLosers = ref([]);
        const allVolume = ref([]);
        const bpjsSignals = ref([]);
        const longTermSignals = ref([]);
        const sectors = ref([]);
        const predictions = ref([]);
        const allPredictions = ref([]);
        const treemapLoading = ref(false);
        const treemapData = ref(null);
        const treemapSectors = ref([]);
        const treemapDate = ref("");
        const dayTradingSignals = ref([]);
        const dayTradingCandidates = ref([]);
        const dayTradingHistory = ref([]);
        const ltAccumulation = ref([]);
        const ltPortfolio = ref([]);
        const ltWatchlist = ref([]);

        const analysisQuery = ref('');
        const analysisSector = ref('All');
        const analysisSectors = ['All', 'Financials', 'Technology', 'Energy', 'Consumer Cycl.', 'Healthcare'];

        const analysisStocks = ref([]);

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
          code: '-', name: '-', price: '-', chg: 0,
          rsi: '-', rsiLabel: '-', macd: '-',
          ma20: '-', ma50: '-', bbUpper: '-', bbLower: '-',
          r2: '-', r1: '-', pivot: '-', s1: '-', s2: '-',
          volume: '-', score: 0, confidence: 0,
          recommendation: 'HOLD', signalClass: 'warning',
          analysis: 'Select a stock to analyze.',
        });

        async function selectStock(item) {
          try {
            const res = await fetch(`/api/analyze/${item.code}`);
            if (!res.ok) throw new Error('Fetch failed');
            const data = await res.json();
            selectedStock.value = {
              code: item.code,
              name: item.name || data.stock_name || '',
              price: data.price ? 'Rp ' + Number(data.price).toLocaleString('id') : '-',
              chg: data.change_pct || 0,
              rsi: data.rsi != null ? String(data.rsi) : '-',
              rsiLabel: data.rsi_status || '-',
              macd: data.macd != null ? (data.macd >= 0 ? '+' : '') + Number(data.macd).toFixed(1) : '-',
              ma20: data.ma20 ? 'Rp ' + Number(data.ma20).toLocaleString('id') : '-',
              ma50: data.ma50 ? 'Rp ' + Number(data.ma50).toLocaleString('id') : '-',
              bbUpper: '-', bbLower: '-',
              r2: data.resistance ? 'Rp ' + Number(data.resistance * 1.05).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-',
              r1: data.resistance ? 'Rp ' + Number(data.resistance).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-',
              pivot: data.price ? 'Rp ' + Number(data.price).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-',
              s1: data.support ? 'Rp ' + Number(data.support).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-',
              s2: data.support ? 'Rp ' + Number(data.support * 0.95).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '-',
              volume: data.volume ? Number(data.volume).toLocaleString('id') : '-',
              score: data.confidence || item.score || 50,
              confidence: data.confidence || item.score || 50,
              recommendation: data.recommendation || 'HOLD',
              signalClass: (data.recommendation === 'BUY' || data.recommendation === 'ENTER') ? 'success' :
                           (data.recommendation === 'SELL') ? 'danger' : 'warning',
              analysis: data.full_analysis || data.reason || 'Analysis not available.',
            };
          } catch(e) {
            console.error('Analyze failed:', e);
            selectedStock.value = {
              code: item.code, name: item.name || '', price: '-', chg: 0,
              rsi: '-', rsiLabel: '-', macd: '-',
              ma20: '-', ma50: '-', bbUpper: '-', bbLower: '-',
              r2: '-', r1: '-', pivot: '-', s1: '-', s2: '-',
              volume: '-', score: item.score || 50, confidence: item.score || 50,
              recommendation: 'HOLD', signalClass: 'warning',
              analysis: 'Gagal mengambil data analisis dari server.',
            };
          }
          currentTab.value = 'detail';
        }

        const comparisonStocks = ref([]);
        const comparisonAddCode = ref('');

        const comparisonRows = computed(() => [
          { label: 'Price', getValue: s => s.price },
          { label: 'Change %', getValue: s => s.chg, getClass: s => s.chg && s.chg.startsWith('+') ? 'profit-positive' : 'profit-negative' },
          { label: 'RSI (14)', getValue: s => s.rsi },
          { label: 'MACD', getValue: s => s.macd, getClass: s => s.macd && s.macd.startsWith('+') ? 'profit-positive' : 'profit-negative' },
          { label: 'Volume', getValue: s => s.volume },
          { label: 'AI Score', getValue: s => s.score, getClass: s => parseInt(s.score) >= 80 ? 'profit-positive' : parseInt(s.score) >= 60 ? '' : 'profit-negative' },
          { label: 'Recommendation', getValue: s => s.rec, getClass: s => s.rec === 'BUY' ? 'profit-positive' : s.rec === 'SELL' ? 'profit-negative' : '' },
        ]);

        const comparisonAvailable = computed(() => {
          const used = new Set(comparisonStocks.value.map(s => s.code));
          return allStocks.value.filter(s => !used.has(s.code)).map(s => s.code);
        });

        async function addComparison() {
          if (!comparisonAddCode.value) return;
          try {
            const res = await fetch('/api/analyze/' + comparisonAddCode.value);
            if (!res.ok) throw new Error('fetch failed');
            const d = await res.json();
            comparisonStocks.value.push({
              code: comparisonAddCode.value,
              price: d.price ? Number(d.price).toLocaleString('id') : '-',
              chg: d.change_pct != null ? (d.change_pct >= 0 ? '+' : '') + d.change_pct + '%' : '0%',
              rsi: d.rsi != null ? String(d.rsi) : '50',
              macd: d.macd != null ? (d.macd >= 0 ? '+' : '') + Number(d.macd).toFixed(1) : '0',
              volume: d.volume ? Number(d.volume).toLocaleString('id') : '-',
              score: String(d.confidence || 50),
              rec: d.recommendation || 'HOLD',
            });
          } catch(e) { console.error('Comparison add failed:', e); }
          comparisonAddCode.value = '';
        }

        const settingsLanguage = ref('en');
        const settingsRiskTolerance = ref('medium');
        const settingsTargetProfit = ref('5');
        const settingsEmailNotif = ref(true);
        const settingsPushNotif = ref(true);

        const settingsAlerts = ref([]);

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

        function formatVolume(v) {
          if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
          if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
          if (v >= 1e3) return (v / 1e3).toFixed(0) + 'K';
          return v.toString();
        }

        function formatPrice(v) {
          return 'Rp ' + Math.round(v).toLocaleString('id-ID');
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
        }

        function applyGainersData(data) {
          const items = (data.gainers || []).map(item => ({
            code: item.code,
            name: item.name,
            chg: (item.change_pct >= 0 ? '+' : '') + item.change_pct.toFixed(1) + '%'
          }));
          movers.value.gainers = items.slice(0, 5);
          allGainers.value = items;
        }

        function applyLosersData(data) {
          const items = (data.losers || []).map(item => ({
            code: item.code,
            name: item.name,
            chg: (item.change_pct >= 0 ? '+' : '') + item.change_pct.toFixed(1) + '%'
          }));
          movers.value.losers = items.slice(0, 5);
          allLosers.value = items;
        }

        function applyVolumeData(data) {
          const items = (data.volumes || []).map(item => ({
            code: item.code,
            name: item.name,
            vol: formatVolume(item.volume)
          }));
          movers.value.volume = items.slice(0, 5);
          allVolume.value = items;
        }

        function applySectorsData(data) {
          sectors.value = Object.entries(data).map(([name, info]) => {
            const perf = info.performance;
            const isPos = perf >= 0;
            const width = Math.min(Math.abs(perf) * 10, 100);
            const color = isPos ? 'var(--success)' : 'var(--danger)';
            let flowClass = 'accent';
            if (info.flow === 'INFLOW') flowClass = 'success';
            else if (info.flow === 'OUTFLOW') flowClass = 'danger';
            return {
              name,
              width: width + '%',
              barColor: color,
              textColor: color,
              change: (isPos ? '+' : '') + perf.toFixed(2) + '%',
              flow: info.flow,
              flowClass
            };
          });
        }

        function applyDaytradeData(data) {
          if (data.status === 'ok' && data.data && data.data.candidates && data.data.candidates.length > 0) {
            bpjsSignals.value = data.data.candidates.map(c => ({
              code: c.code,
              signal: c.signal,
              signalClass: c.signal === 'ENTER' ? 'success' : c.signal === 'WAIT' ? 'warning' : 'danger',
              confidence: c.confidence,
              price: formatPrice(c.price)
            }));
          }
        }

        function applyLongtermData(data) {
          if (data.status === 'ok' && data.data && data.data.candidates && data.data.candidates.length > 0) {
            longTermSignals.value = data.data.candidates.map(c => ({
              code: c.code,
              signal: c.signal,
              signalClass: c.signalClass || (c.signal === 'Active Accum' ? 'accent' : c.signal === 'Accum Watch' ? 'warning' : 'danger'),
              confidence: c.confidence,
              entryZone: c.entryZone
            }));
          }
        }

        function applyForeignData(data) {
          if (data.status === 'ok' && data.data) {
            const items = [];
            (data.data.top_accumulating || []).forEach(item => {
              items.push({
                code: item.code,
                phase: 'Active Accum',
                signalClass: 'accent',
                confidence: item.confidence || 0,
                entryZone: item.entry_zone || 'N/A',
                accumDays: item.accum_days || 0,
                rsStatus: item.rs_status || 'Neutral'
              });
            });
            (data.data.top_distributing || []).forEach(item => {
              items.push({
                code: item.code,
                phase: 'Distribution',
                signalClass: 'danger',
                confidence: item.confidence || 0,
                entryZone: 'N/A',
                accumDays: 0,
                rsStatus: 'Weak'
              });
            });
            if (items.length > 0) ltAccumulation.value = items;
          }
        }

        async function loadAllData() {
          const [marketRes, gainersRes, losersRes, volumeRes, sectorsRes, daytradeRes, longtermRes, foreignRes] = await Promise.allSettled([
            fetch('/api/market-summary').then(r => r.json()),
            fetch('/api/top-gainers?limit=5').then(r => r.json()),
            fetch('/api/top-losers?limit=5').then(r => r.json()),
            fetch('/api/top-volume?limit=5').then(r => r.json()),
            fetch('/api/sector-performance').then(r => r.json()),
            fetch('/api/day-trade/candidates').then(r => r.json()),
            fetch('/api/long-term/candidates').then(r => r.json()),
            fetch('/api/foreign-flow/summary').then(r => r.json())
          ]);
          if (marketRes.status === 'fulfilled') applyMarketData(marketRes.value);
          if (gainersRes.status === 'fulfilled') applyGainersData(gainersRes.value);
          if (losersRes.status === 'fulfilled') applyLosersData(losersRes.value);
          if (volumeRes.status === 'fulfilled') applyVolumeData(volumeRes.value);
          if (sectorsRes.status === 'fulfilled') applySectorsData(sectorsRes.value);
          if (daytradeRes.status === 'fulfilled') applyDaytradeData(daytradeRes.value);
          if (longtermRes.status === 'fulfilled') applyLongtermData(longtermRes.value);
          if (foreignRes.status === 'fulfilled') applyForeignData(foreignRes.value);
        }

        function renderMrCharts(full) {
          const sorted = [...full].reverse();
          const labels = sorted.map(r => r.date);
          const ihsgData = sorted.map(r => r.ihsg_change);

          if (ihsgChartInstance) ihsgChartInstance.destroy();
          const ctx1 = document.getElementById('ihsgChart');
          if (ctx1) {
            const hasIHSG = ihsgData.some(v => v !== null);
            ihsgChartInstance = new Chart(ctx1, {
              type: 'line',
              data: { labels, datasets: [{ label: 'IHSG Change %', data: ihsgData, borderColor: '#7C3AED', backgroundColor: 'rgba(124,58,237,0.1)', tension: 0.3, fill: true, pointRadius: 1.5, pointHoverRadius: 4, borderWidth: 2 }] },
              options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#333' }, ticks: { callback: v => v.toFixed(2) + '%' } }, x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } } } }
            });
            if (!hasIHSG) {
              // Show "no data" overlay
              const parent = ctx1.parentElement;
              if (parent && !parent.querySelector('.chart-no-data')) {
                const nd = document.createElement('div');
                nd.className = 'chart-no-data';
                nd.innerHTML = '⚠️ Belum ada data IHSG';
                nd.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:14px;z-index:10;pointer-events:none';
                parent.style.position = 'relative';
                parent.appendChild(nd);
              }
            }
          }

          const fMap = {};
          full.forEach(r => {
            (r.foreign_buy || []).forEach(s => {
              if (!fMap[s.stock]) fMap[s.stock] = { net: 0 };
              fMap[s.stock].net += s.value;
            });
            (r.local_buy || []).forEach(s => {
              if (!fMap[s.stock]) fMap[s.stock] = { net: 0 };
              fMap[s.stock].net -= s.value;
            });
          });
          const fSorted = Object.entries(fMap).filter(([,v]) => v.net > 0).sort((a,b) => b[1].net - a[1].net).slice(0, 10);

          if (foreignChartInstance) foreignChartInstance.destroy();
          const ctx2 = document.getElementById('foreignChart');
          if (ctx2) {
            const hasForeignData = fSorted.length > 0;
            const fColors = fSorted.map(([,v]) => v.net >= 0 ? '#7C3AED' : '#EF5350');
            foreignChartInstance = new Chart(ctx2, {
              type: 'bar',
              data: { labels: fSorted.map(([k]) => k), datasets: [{ label: 'Net Foreign (Rp)', data: fSorted.map(([,v]) => v.net), backgroundColor: fColors, borderRadius: 4 }] },
              options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#333' }, ticks: { callback: v => formatRp(v) } }, x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } } } }
            });
            if (!hasForeignData) {
              const parent = ctx2.parentElement;
              if (parent && !parent.querySelector('.chart-no-data')) {
                const nd = document.createElement('div');
                nd.className = 'chart-no-data';
                nd.innerHTML = '⚠️ Belum ada data foreign buy';
                nd.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:14px;z-index:10;pointer-events:none';
                parent.style.position = 'relative';
                parent.appendChild(nd);
              }
            }
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
            const full = (json.data || []).filter(r => r.type === 'full' || r.type === 'akhir_sesi' || r.type === 'sesi1');
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

        function switchMrTab(tab) {
          currentTab.value = tab;
          if (tab === 'overview') setTimeout(() => renderMrCharts(mrReports.value), 100);
          if (tab === 'analysis' && !mrAnalysis.value) loadMrAnalysis();
        }

        function switchView(view, tab) {
          currentView.value = view;
          if (view === 'marketreports') loadMarketReports();
          if (view === 'daytrading') loadDayTradingData();
          if (view === 'longterm') loadForeignFlowData();
          if (view === 'analysis') loadStocks();
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
          loadDayTradingData();
          currentTab.value = 'signals';
        }

        function mockSave() {
          alert('Settings saved (local only).');
        }

        // ── Data Loaders ──

        async function loadMarketSummary() {
          try {
            const [sumRes, sentRes] = await Promise.all([
              fetch('/api/market-summary'),
              fetch('/api/market-sentiment'),
            ]);
            const sum = await sumRes.json();
            const sent = await sentRes.json();
            const fg = sent.fear_greed || sum.fear_greed || { index: 50, label: 'Neutral' };
            const vol = sum.total_volume || 0;
            const volStr = vol >= 1e12 ? (vol/1e12).toFixed(1)+'T' : vol >= 1e9 ? (vol/1e9).toFixed(1)+'B' : vol >= 1e6 ? (vol/1e6).toFixed(1)+'M' : String(vol);
            market.value = {
              fgi: { value: fg.index || 50, label: fg.label || 'Neutral' },
              advancing: { count: sum.advancing || 0, change: '+0', pct: sum.total_stocks ? Math.round(sum.advancing/sum.total_stocks*100)+'%' : '0%' },
              declining: { count: sum.declining || 0, change: '0', pct: sum.total_stocks ? Math.round(sum.declining/sum.total_stocks*100)+'%' : '0%' },
              avgChange: (sum.avg_change != null ? (sum.avg_change >= 0 ? '+' : '') + sum.avg_change + '%' : '0%'),
              totalVolume: volStr,
              volumeChange: '-',
              status: 'Open',
              hours: '09:00 \u2013 15:00 WIB',
            };
          } catch(e) { console.error('Market summary load failed:', e); }
        }

        async function loadTopMovers() {
          try {
            const [gRes, lRes, vRes] = await Promise.all([
              fetch('/api/top-gainers?limit=10'),
              fetch('/api/top-losers?limit=10'),
              fetch('/api/top-volume?limit=10'),
            ]);
            const g = await gRes.json();
            const l = await lRes.json();
            const v = await vRes.json();
            const fmt = items => items.map(s => ({
              code: s.code, name: s.name || s.stock_name || '',
              chg: (s.change_pct >= 0 ? '+' : '') + s.change_pct + '%',
              vol: s.volume ? (s.volume >= 1e9 ? (s.volume/1e9).toFixed(1)+'B' : (s.volume/1e6).toFixed(1)+'M') : '-',
            }));
            const gainers = (g.gainers || []).slice(0,3);
            const losers = (l.losers || []).slice(0,3);
            const volume = (v.volumes || []).slice(0,3);
            movers.value = { gainers: fmt(gainers), losers: fmt(losers), volume: fmt(volume) };
            allGainers.value = fmt(g.gainers || []);
            allLosers.value = fmt(l.losers || []);
            allVolume.value = fmt(v.volumes || []);
          } catch(e) { console.error('Top movers load failed:', e); }
        }

        async function loadSectors() {
          try {
            const res = await fetch('/api/sector-performance');
            const data = await res.json();
            const maxPerf = Math.max(...Object.values(data).map(s => Math.abs(s.performance)), 0.01);
            sectors.value = Object.entries(data).map(([name, s]) => {
              const perf = s.performance;
              const pct = perf >= 0 ? perf : -perf;
              const width = Math.max(8, Math.min(100, (pct / maxPerf) * 100));
              const isPos = perf >= 0;
              const barColor = isPos ? 'var(--success)' : 'var(--danger)';
              const flowMap = { INFLOW: { label: 'Inflow', cls: 'success' }, OUTFLOW: { label: 'Outflow', cls: 'danger' }, NEUTRAL: { label: 'Neutral', cls: 'accent' } };
              const f = flowMap[s.flow] || flowMap.NEUTRAL;
              return {
                name, width: width + '%', barColor, textColor: barColor,
                change: (perf >= 0 ? '+' : '') + perf.toFixed(2) + '%',
                flow: f.label, flowClass: f.cls,
              };
            });
          } catch(e) { console.error('Sectors load failed:', e); }
        }

        async function loadStocks() {
          try {
            const res = await fetch('/api/stocks');
            const data = await res.json();
            // Minimal sector map for analysis filtering
            const SECTOR_GUESS = {
              BBCA:'Financials', BBRI:'Financials', BMRI:'Financials', BBNI:'Financials',
              TLKM:'Technology', EXCL:'Technology', TOWR:'Technology',
              ASII:'Consumer Cycl.', UNVR:'Consumer Cycl.', INDF:'Consumer Cycl.', ICBP:'Consumer Cycl.', HMSP:'Consumer Cycl.', GGRM:'Consumer Cycl.',
              ADRO:'Energy', ITMG:'Energy', PTBA:'Energy', MEDC:'Energy',
              CPIN:'Healthcare', KLBF:'Healthcare',
              JSMR:'Infrastructure', PGAS:'Infrastructure', SMGR:'Infrastructure', INTP:'Infrastructure', SMMA:'Infrastructure', AKRA:'Infrastructure',
              GOTO:'Technology',
            };
            allStocks.value = (data.stocks || []).map(s => ({
              code: s.code, name: s.name || '',
              chg: 0, price: '-', sector: SECTOR_GUESS[s.code] || 'Other', score: 0,
            }));
            // Also prime analysis stocks
            analysisStocks.value = allStocks.value;
            // Load scores for first batch
            allStocks.value.forEach((s, i) => {
              fetch('/api/analyze/' + s.code).then(r => r.json()).then(d => {
                if (d.stock_code) {
                  const chg = d.change_pct || 0;
                  s.chg = chg;
                  s.price = d.price ? 'Rp ' + Number(d.price).toLocaleString('id') : '-';
                  s.score = d.confidence || 50;
                  if (analysisStocks.value[i]) {
                    analysisStocks.value[i] = { ...analysisStocks.value[i], chg, price: s.price, score: s.score };
                  }
                }
              }).catch(() => {});
            });
          } catch(e) { console.error('Stocks load failed:', e); }
        }

        async function loadWatchlistData() {
          try {
            const res = await fetch('/api/watchlist/1');
            const data = await res.json();
            watchlist.value = (data.watchlist || []).map(w => ({ code: w.stock_code || w.code || '', chg: 0 }));
            ltWatchlist.value = (data.watchlist || []).map(w => ({
              code: w.stock_code || w.code || '', name: '', chg: 0, volume: '-', sector: '-',
            }));
            // Fetch changes for each
            watchlist.value.forEach(w => {
              fetch('/api/stock/' + w.code).then(r => r.json()).then(d => {
                w.chg = d.change_pct || 0;
              }).catch(() => {});
            });
          } catch(e) { console.error('Watchlist load failed:', e); }
        }

        async function loadDayTradingData() {
          try {
            const res = await fetch('/api/day-trade/candidates');
            const json = await res.json();
            const candidates = (json.data && json.data.candidates) || [];
            const signalMap = { ENTER: { cls: 'success' }, WAIT: { cls: 'warning' }, AVOID: { cls: 'danger' }, HOLD: { cls: 'accent' } };
            dayTradingSignals.value = candidates.map(c => {
              const sig = signalMap[c.action] || signalMap.WAIT;
              return {
                code: c.stock_code,
                signal: c.action,
                signalClass: sig.cls,
                confidence: c.confidence || 0,
                price: c.current_price ? 'Rp ' + Number(c.current_price).toLocaleString('id') : '-',
                entry: c.entry_price ? 'Rp ' + Number(c.entry_price).toLocaleString('id') : '-',
                exit: c.target_profit ? 'Rp ' + Number(c.target_profit).toLocaleString('id') : '-',
              };
            });
            dayTradingCandidates.value = candidates.map(c => ({
              stock: c.stock_code,
              signal: c.action,
              signalClass: signalMap[c.action] ? signalMap[c.action].cls : 'warning',
              conf: c.confidence || 0,
              entry: c.entry_price ? Number(c.entry_price).toLocaleString('id') : '-',
              tp: c.target_profit ? Number(c.target_profit).toLocaleString('id') : '-',
              cl: c.cut_loss ? Number(c.cut_loss).toLocaleString('id') : '-',
              volRatio: c.volume_ratio ? c.volume_ratio.toFixed(1) + 'x' : '-',
              foreignFlow: c.foreign_flow_status || '-',
              action: c.action === 'ENTER' ? 'Buy' : 'Watch',
            }));
            // Top 4 as signal cards on overview
            bpjsSignals.value = dayTradingSignals.value.slice(0, 4);
          } catch(e) { console.error('Day trade load failed:', e); }
        }

        async function loadForeignFlowData() {
          try {
            const res = await fetch('/api/foreign-flow/summary');
            const json = await res.json();
            const acc = (json.data && json.data.top_accumulating) || [];
            longTermSignals.value = acc.map(a => ({
              code: a.stock_code,
              signal: a.strength === 'strong' ? 'Active Accum' : a.strength === 'moderate' ? 'Accum Watch' : 'Early Accum',
              signalClass: a.strength === 'strong' ? 'accent' : a.strength === 'moderate' ? 'warning' : 'accent',
              confidence: Math.min(99, Math.round((a.accumulation_days || 0) * 3 + 50)),
              entryZone: a.cumulative_net ? 'Rp ' + Number(a.cumulative_net/1000000).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : 'N/A',
            }));
            ltAccumulation.value = acc.map(a => ({
              code: a.stock_code,
              phase: a.strength === 'strong' ? 'Active Accum' : a.strength === 'moderate' ? 'Accum Watch' : 'Early Accum',
              signalClass: a.strength === 'strong' ? 'accent' : 'warning',
              confidence: Math.min(99, Math.round((a.accumulation_days || 0) * 3 + 50)),
              entryZone: a.cumulative_net ? Number(a.cumulative_net/1000000).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') : 'N/A',
              accumDays: a.accumulation_days || 0,
              rsStatus: a.strength || 'Neutral',
            }));
          } catch(e) { console.error('Foreign flow load failed:', e); }
        }

        async function loadAnalysisHistory() {
          try {
            const res = await fetch('/api/analysis-history?limit=20');
            const json = await res.json();
            const history = json.history || [];
            if (history.length) {
              const wins = history.filter(h => h.result === 'win' || h.result === 'success');
              const total = history.length;
              const winRate = total ? Math.round(wins.length / total * 100) : 0;
              aiPerf.value = {
                accuracy: winRate + '%',
                accuracyChange: '-',
                winRate: winRate + '%',
                winRateChange: '-',
                avgProfit: history.reduce((a, h) => a + (h.profit_pct || 0), 0) / total + '%',
                totalPredictions: String(total),
              };
              // Format for tables
              const fmtHistory = history.map(h => ({
                code: h.stock_code || h.code || '-',
                signal: h.prediction || h.signal || 'HOLD',
                signalClass: (h.prediction === 'BUY' || h.prediction === 'ENTER') ? 'success' : h.prediction === 'SELL' ? 'danger' : 'warning',
                confidence: h.confidence || 50,
                result: h.result === 'win' ? 'Win' : h.result === 'loss' ? 'Loss' : 'Pending',
                resultClass: h.result === 'win' ? 'success' : h.result === 'loss' ? 'danger' : 'warning',
                profit: (h.profit_pct >= 0 ? '+' : '') + (h.profit_pct || 0) + '%',
                profitClass: (h.profit_pct || 0) >= 0 ? 'profit-positive' : 'profit-negative',
                date: h.created_at ? h.created_at.slice(5, 10) : '-',
              }));
              predictions.value = fmtHistory.slice(0, 5);
              allPredictions.value = fmtHistory;
              dayTradingHistory.value = fmtHistory.filter(h => h.code).map(h => ({
                date: h.date, stock: h.code, entry: '-', exit: '-',
                profit: h.profit, profitClass: h.profitClass, result: h.result, resultClass: h.resultClass,
              }));
            }
          } catch(e) { console.error('Analysis history load failed:', e); }
        }

        async function loadAlerts() {
          try {
            const res = await fetch('/api/alerts?limit=20');
            const json = await res.json();
            settingsAlerts.value = (json.alerts || []).map(a => ({
              stock: a.stock_code || a.code || '-',
              type: a.alert_type || a.type || 'Price Alert',
              condition: a.condition || '-',
              status: a.status || 'Inactive',
            }));
          } catch(e) { console.error('Alerts load failed:', e); }
        }

        async function loadAllDashboardData() {
          await Promise.allSettled([
            loadMarketSummary(),
            loadTopMovers(),
            loadSectors(),
            loadStocks(),
            loadWatchlistData(),
            loadDayTradingData(),
            loadForeignFlowData(),
            loadAnalysisHistory(),
            loadAlerts(),
          ]);
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
          if (tab === 'treemap') fetchTreemapData();
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

        async function fetchTreemapData() {
          if (treemapLoading.value) return;
          treemapLoading.value = true;
          try {
            const res = await fetch('/api/treemap');
            const data = await res.json();
            treemapData.value = data;
            treemapSectors.value = data.sectors || [];
            treemapDate.value = data.date || '';
          } catch (e) {
            console.error('Treemap fetch error:', e);
            return;
          } finally {
            treemapLoading.value = false;
          }
          // Wait for DOM to render container, then draw treemap
          await Vue.nextTick();
          renderTreemap(treemapData.value);
        }

        function renderTreemap(data) {
          const el = document.getElementById('treemap-container');
          if (!el || !data || !data.sectors || !data.sectors.length) {
            console.warn('Treemap: no data or container');
            return;
          }
          console.log('Treemap render start, sectors:', data.sectors.length);
          el.innerHTML = '';
          el.style.position = 'relative';

          const W = el.clientWidth || 900;
          const H = el.clientHeight || 640;

          const svg = d3.select(el).append('svg')
            .attr('width', W)
            .attr('height', H)
            .style('background', '#1a1a2e');

          // Color scale: red→gray→green
          const c = d3.scaleLinear()
            .domain([-8, -2, 0, 2, 8])
            .range(['#ef4444', '#a05252', '#6b7280', '#16a34a', '#22c55e'])
            .clamp(true);

          // Build proper nested hierarchy: root → sectors → stocks
          // d3.hierarchy needs {children: [...]} — rename stocks→children
          const treemapInput = {
            children: data.sectors.map(function(sector) {
              return {
                name: sector.name,
                stock_count: sector.stock_count,
                change_pct: sector.change_pct,
                total_size: sector.total_size,
                children: sector.stocks.map(function(stock) {
                  return {
                    code: stock.code,
                    change_pct: stock.change_pct,
                    close: stock.close,
                    volume: stock.volume,
                    size: stock.size,
                    sector: sector.name,
                  };
                }),
              };
            }),
          };

          const root = d3.hierarchy(treemapInput)
            .sum(function(d) { return d.size || d.total_size || 0; })
            .sort(function(a, b) { return (b.value || 0) - (a.value || 0); });

          console.log('Hierarchy leaves:', root.leaves().length);

          var layout = d3.treemap()
            .size([W, H - 40])
            .paddingOuter(3)
            .paddingTop(20)
            .paddingInner(2)
            .round(true);

          layout(root);

          // Draw sector group background rects — fill allocated area with subtle color
          svg.selectAll('g.sector-bg')
            .data(root.children || [])
            .enter().append('rect')
            .attr('x', function(d) { return d.x0; })
            .attr('y', function(d) { return d.y0; })
            .attr('width', function(d) { return d.x1 - d.x0; })
            .attr('height', function(d) { return d.y1 - d.y0; })
            .attr('fill', function(d) {
              var pct = d.data.change_pct || 0;
              return pct >= 0 ? '#162b1a' : '#2b1616';
            })
            .attr('rx', 3)
            .attr('stroke', '#2a2a4e')
            .attr('stroke-width', 1);

          // Draw leaves (stocks)
          var leaf = svg.selectAll('g.leaf')
            .data(root.leaves())
            .enter().append('g')
            .attr('transform', function(d) {
              return 'translate(' + d.x0 + ',' + d.y0 + ')';
            });

          leaf.append('rect')
            .attr('width', function(d) { return d.x1 - d.x0; })
            .attr('height', function(d) { return d.y1 - d.y0; })
            .attr('fill', function(d) { return c(d.data.change_pct || 0); })
            .attr('rx', 2)
            .attr('stroke', '#1a1a2e')
            .attr('stroke-width', 1);

          leaf.append('text')
            .attr('x', 4)
            .attr('y', 14)
            .attr('fill', '#fff')
            .attr('font-size', '10px')
            .attr('font-weight', 'bold')
            .style('pointer-events', 'none')
            .style('text-shadow', '0 1px 3px rgba(0,0,0,0.8)')
            .text(function(d) { return d.data.code || ''; });

          leaf.append('text')
            .attr('x', 4)
            .attr('y', 26)
            .attr('fill', '#fff')
            .attr('font-size', '9px')
            .style('pointer-events', 'none')
            .style('text-shadow', '0 1px 3px rgba(0,0,0,0.8)')
            .text(function(d) {
              var pct = d.data.change_pct || 0;
              return (pct >= 0 ? '+' : '') + pct + '%';
            });

          // Sector group labels
          svg.selectAll('g.slabel')
            .data(root.children || [])
            .enter().append('text')
            .attr('x', function(d) { return d.x0 + 6; })
            .attr('y', function(d) { return d.y0 + 14; })
            .attr('fill', '#94a3b8')
            .attr('font-size', '10px')
            .attr('font-weight', 'bold')
            .style('pointer-events', 'none')
            .style('text-shadow', '0 1px 3px rgba(0,0,0,0.8)')
            .text(function(d) {
              return d.data.name + ' (' + (d.data.stock_count || 0) + ')';
            });

          // Tooltip
          var tt = d3.select(el).append('div')
            .attr('class', 'treemap-tooltip')
            .style('position', 'absolute')
            .style('background', 'rgba(15,15,35,0.95)')
            .style('color', '#fff')
            .style('padding', '8px 12px')
            .style('border-radius', '6px')
            .style('border', '1px solid #333')
            .style('font-size', '12px')
            .style('pointer-events', 'none')
            .style('opacity', '0')
            .style('z-index', '1000');

          leaf.on('mouseover', function(event, d) {
            var s = d.data;
            var pct = s.change_pct || 0;
            var sign = pct >= 0 ? '+' : '';
            var formattedClose = (s.close || 0).toLocaleString();
            var formattedVol = ((s.volume || 0) / 1e6).toFixed(1);
            tt.html(
              '<b style="color:#7C3AED">' + s.code + '</b><br/>' +
              'Change: <b>' + sign + pct + '%</b><br/>' +
              'Price: ' + formattedClose + '<br/>' +
              'Vol: ' + formattedVol + 'M<br/>' +
              '<span style="color:#94a3b8">' + s.sector + '</span>'
            )
            .style('opacity', '1')
            .style('left', (event.offsetX + 12) + 'px')
            .style('top', (event.offsetY - 10) + 'px');
          })
          .on('mousemove', function(event) {
            tt.style('left', (event.offsetX + 12) + 'px')
              .style('top', (event.offsetY - 10) + 'px');
          })
          .on('mouseleave', function() {
            tt.style('opacity', '0');
          });

          // Color legend bar at bottom
          var lx = (W / 2) - 100;
          var ly = H - 18;

          var grad = svg.append('defs').append('linearGradient')
            .attr('id', 'tm-grad');

          grad.selectAll('stop')
            .data([-8, -5, -2, 0, 2, 5, 8])
            .enter().append('stop')
            .attr('offset', function(d) { return ((d + 8) / 16 * 100) + '%'; })
            .attr('stop-color', function(d) { return c(d); });

          svg.append('rect')
            .attr('x', lx)
            .attr('y', ly)
            .attr('width', 200)
            .attr('height', 8)
            .attr('rx', 3)
            .style('fill', 'url(#tm-grad)');

          var ls = d3.scaleLinear().domain([-8, 8]).range([0, 200]);
          svg.append('g')
            .attr('transform', 'translate(' + lx + ',' + (ly + 8) + ')')
            .attr('color', '#94a3b8')
            .style('font-size', '9px')
            .call(d3.axisBottom(ls).ticks(5).tickFormat(function(d) { return d + '%'; }))
            .call(function(g) { g.select('.domain').attr('stroke', 'none'); });

          console.log('Treemap rendered:', root.leaves().length, 'stocks');
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
          // Load foreign overview data for dashboard
          loadForeignOverview();
          // Listen for hash changes (browser back/forward)
          window.addEventListener('hashchange', () => {
            const prevView = currentView.value;
            const prevTab = currentTab.value;
            syncViewFromUrl();
          });
          loadAllData();
        });

        return {
          currentTheme, currentView, currentTab, searchQuery, sidebarOpen, searchOpen, dateStr,
          themes, navItems, headerTitle,
          dashboardTabs, daytradingTabs, longtermTabs, analysisTabs, settingsTabs,
          watchlist, allStocks, filteredStocks,
          market, aiPerf, aiPerfDetails, movers,
          allGainers, allLosers, allVolume,
          bpjsSignals, longTermSignals, sectors, predictions, allPredictions,
          treemapLoading, treemapData, treemapSectors, treemapDate,
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
          mrNetForeign, mrSortKey, mrSortDir, toggleMrSort, mrSortIcon, mrSortedForeign,
          foreignOverviewStocks, pahlawanBursaStocks, dailyNetTotal, foreignStockCount, foreignActivitySummary,
          formatRp, loadMarketReports, loadMrAnalysis, loadForeignOverview, switchMrTab,
        };
      }
    }).mount('#app');
