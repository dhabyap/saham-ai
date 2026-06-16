// ─── Chart.js Rendering ───
// Depends on: utils.js (formatRp), state.js (mrReports)

let ihsgChartInstance = null;
let foreignChartInstance = null;

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
