    const { createApp, ref, computed, onMounted, watch } = Vue;

    createApp({
      setup() {
        const currentTheme = ref('neumorphism');
        const currentView = ref('marketreports');
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
        let ihsgChartInstance = null;
        let foreignChartInstance = null;

        const themes = [
          { id: 'neumorphism', label: 'Light' },
          { id: 'dark', label: 'Dark' },
          { id: 'classy', label: 'Classy' },
        ];

        const navItems = [
          { view: 'marketreports', icon: '📊', label: 'Market Reports' },
        ];

        const headerTitle = computed(() => 'Market Reports');

        const watchlist = ref([]);
        const allStocks = ref([]);

        const filteredStocks = computed(() => {
          const q = searchQuery.value.toLowerCase();
          if (!q) return allStocks.value;
          return allStocks.value.filter(s =>
            s.code.toLowerCase().includes(q) || s.name.toLowerCase().includes(q)
          );
        });

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
          if (tab === 'backtest' && !mrBtData.value) loadBacktest();
        }

        function setMrFilter(filter) {
          mrFilter.value = filter;
          loadMarketReports();
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

        // ── Data Loaders ──

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

        let _viewChanging = false;

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
          syncViewFromUrl();
          loadForeignOverview();
          window.addEventListener('hashchange', () => {
            syncViewFromUrl();
          });
          // Load market reports on startup
          loadMarketReports();
          loadStocks();
          loadWatchlistData();
        });

        return {
          currentTheme, currentView, currentTab, searchQuery, sidebarOpen, searchOpen, dateStr,
          themes, navItems, headerTitle,
          watchlist, allStocks, filteredStocks,
          mrReports, mrStats, mrForeignStocks, mrLocalStocks,
          mrAnalysis, mrLoadingAnalysis,
          mrFilter, mrBtData, mrBtLoading, mrBtError,
          mrMonths, mrExpandedMonths, toggleMonth,
          mrNetForeign, mrSortKey, mrSortDir, toggleMrSort, mrSortIcon, mrSortedForeign,
          foreignOverviewStocks, pahlawanBursaStocks, dailyNetTotal, foreignStockCount, foreignActivitySummary,
          formatRp, loadMarketReports, loadMrAnalysis, loadForeignOverview, switchMrTab, setMrFilter, loadBacktest,
          switchView, switchTheme, toggleSidebar, closeSearch, onSearchInput,
        };
      }
    }).mount('#app');
