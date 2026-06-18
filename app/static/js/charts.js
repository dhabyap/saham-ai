// ─── Chart.js Rendering ───
// Depends on: utils.js (formatRp), state.js (mrReports)

var ihsgChartInstance = null;
var foreignChartInstance = null;
var shBarChartInstance = null;
var shDoughnutInstance = null;

function renderMrCharts(full) {
  var sorted = full.slice().reverse();
  var labels = sorted.map(function(r) { return r.date; });
  var ihsgData = sorted.map(function(r) { return r.ihsg_change; });

  if (ihsgChartInstance) { ihsgChartInstance.destroy(); ihsgChartInstance = null; }
  var ctx1 = document.getElementById('ihsgChart');
  if (ctx1) {
    var hasIHSG = ihsgData.some(function(v) { return v !== null; });
    ihsgChartInstance = new Chart(ctx1, {
      type: 'line',
      data: { labels: labels, datasets: [{ label: 'IHSG Change %', data: ihsgData, borderColor: '#7C3AED', backgroundColor: 'rgba(124,58,237,0.1)', tension: 0.3, fill: true, pointRadius: 1.5, pointHoverRadius: 4, borderWidth: 2 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#333' }, ticks: { callback: function(v) { return v.toFixed(2) + '%'; } } }, x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } } } }
    });
    if (!hasIHSG) {
      var parent = ctx1.parentElement;
      if (parent && !parent.querySelector('.chart-no-data')) {
        var nd = document.createElement('div');
        nd.className = 'chart-no-data';
        nd.innerHTML = '⚠️ Belum ada data IHSG';
        nd.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:14px;z-index:10;pointer-events:none';
        parent.style.position = 'relative';
        parent.appendChild(nd);
      }
    }
  }

  // Foreign chart
  var fMap = {};
  full.forEach(function(r) {
    (r.foreign_buy || []).forEach(function(s) {
      if (!fMap[s.stock]) fMap[s.stock] = { net: 0 };
      fMap[s.stock].net += s.value;
    });
    (r.local_buy || []).forEach(function(s) {
      if (!fMap[s.stock]) fMap[s.stock] = { net: 0 };
      fMap[s.stock].net -= s.value;
    });
  });
  var fSorted = Object.entries(fMap).filter(function(kv) { return kv[1].net > 0; }).sort(function(a,b) { return b[1].net - a[1].net; }).slice(0, 10);

  if (foreignChartInstance) { foreignChartInstance.destroy(); foreignChartInstance = null; }
  var ctx2 = document.getElementById('foreignChart');
  if (ctx2) {
    var hasFD = fSorted.length > 0;
    var fColors = fSorted.map(function(kv) { return kv[1].net >= 0 ? '#7C3AED' : '#EF5350'; });
    foreignChartInstance = new Chart(ctx2, {
      type: 'bar',
      data: { labels: fSorted.map(function(kv) { return kv[0]; }), datasets: [{ label: 'Net Foreign (Rp)', data: fSorted.map(function(kv) { return kv[1].net; }), backgroundColor: fColors, borderRadius: 4 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { color: '#333' }, ticks: { callback: function(v) { return formatRp(v); } } }, x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 10 } } } } }
    });
    if (!hasFD) {
      var parent2 = ctx2.parentElement;
      if (parent2 && !parent2.querySelector('.chart-no-data')) {
        var nd2 = document.createElement('div');
        nd2.className = 'chart-no-data';
        nd2.innerHTML = '⚠️ Belum ada data foreign buy';
        nd2.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:14px;z-index:10;pointer-events:none';
        parent2.style.position = 'relative';
        parent2.appendChild(nd2);
      }
    }
  }
}

function buildMrStockTable(dataKey, color) {
  var map = {};
  mrReports.value.forEach(function(r) {
    (r[dataKey] || []).forEach(function(s) {
      if (!map[s.stock]) map[s.stock] = { count: 0, total: 0, lastDate: r.date };
      map[s.stock].count++;
      map[s.stock].total += s.value;
      if (r.date > map[s.stock].lastDate) map[s.stock].lastDate = r.date;
    });
  });
  return Object.entries(map).sort(function(a,b) { return b[1].total - a[1].total; }).map(function(kv) { return { stock: kv[0], count: kv[1].count, total: kv[1].total, lastDate: kv[1].lastDate }; });
}

function renderShareholderCharts() {
  var data = topShareholders.value;
  if (!data || !data.length) return;

  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  // Bar chart
  var top15 = data.slice().sort(function(a,b) { return (b.total_pct||0) - (a.total_pct||0); }).slice(0, 15);
  var labels = top15.map(function(s) { return s.shareholder_name.length > 28 ? s.shareholder_name.substring(0,26)+'...' : s.shareholder_name; });
  var vals = top15.map(function(s) { return parseFloat((s.total_pct||0).toFixed(2)); });

  var ctx1 = document.getElementById('shBarChart');
  if (!ctx1) return;
  if (shBarChartInstance) { shBarChartInstance.destroy(); shBarChartInstance = null; }
  shBarChartInstance = new Chart(ctx1, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{ label: 'Total %', data: vals, backgroundColor: vals.map(function(v) { return v >= 100 ? 'rgba(124,58,237,0.7)' : 'rgba(139,92,246,0.5)'; }), borderColor: vals.map(function(v) { return v >= 100 ? '#7C3AED' : '#8B5CF6'; }), borderWidth: 1, borderRadius: 4 }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: function(ctx) { return ctx.raw + '%'; } } } },
      scales: { x: { grid: { color: gridColor }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } }, y: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } } }
    }
  });

  // Doughnut
  var buckets = [0,0,0,0,0];
  data.forEach(function(s) {
    var c = s.stock_count || 0;
    if (c <= 5) buckets[0]++;
    else if (c <= 10) buckets[1]++;
    else if (c <= 20) buckets[2]++;
    else if (c <= 50) buckets[3]++;
    else buckets[4]++;
  });
  var ctx2 = document.getElementById('shDoughnutChart');
  if (!ctx2) return;
  if (shDoughnutInstance) { shDoughnutInstance.destroy(); shDoughnutInstance = null; }
  shDoughnutInstance = new Chart(ctx2, {
    type: 'doughnut',
    data: { labels: ['1-5 saham', '6-10 saham', '11-20 saham', '21-50 saham', '50+ saham'], datasets: [{ data: buckets, backgroundColor: ['#8B5CF6','#3B82F6','#F59E0B','#10B981','#EF4444'], borderWidth: 0 }] },
    options: { responsive: true, maintainAspectRatio: false, cutout: '55%', plugins: { legend: { position: 'bottom', labels: { color: textColor, font: { size: 10 }, boxWidth: 10, padding: 8 } } } }
  });
}
