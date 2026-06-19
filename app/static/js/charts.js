// ─── Chart.js Rendering ───
// Depends on: utils.js (formatRp), state.js (mrReports)

var ihsgChartInstance = null;
var foreignChartInstance = null;
var shDistChartInstance = null;
var shTopStockChartInstance = null;
var shTopHolderChartInstance = null;

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

function renderShareholderChartsEnhanced() {
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
  var accent = '#7C3AED';
  var accentLight = 'rgba(124,58,237,0.6)';

  // 1. DONUT — Distribusi Kepemilikan
  var dist = shDistribution.value;
  if (dist && dist.total) {
    var ctx1 = document.getElementById('shDistChart');
    if (ctx1) {
      if (shDistChartInstance) { shDistChartInstance.destroy(); shDistChartInstance = null; }
      shDistChartInstance = new Chart(ctx1, {
        type: 'doughnut',
        data: {
          labels: ['≥5% (Pengendali)', '1-5% (Signifikan)', '0.5-1% (Minoritas)', '<0.5% (Pemodal Kecil)'],
          datasets: [{
            data: [dist.large, dist.medium, dist.small, dist.tiny],
            backgroundColor: ['#EF4444', '#F59E0B', '#3B82F6', '#8B5CF6'],
            borderWidth: 0,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '55%',
          plugins: {
            legend: { position: 'bottom', labels: { color: textColor, font: { size: 10 }, boxWidth: 12, padding: 10 } },
            tooltip: {
              callbacks: {
                label: function(ctx) {
                  var total = dist.total;
                  var pct = ((ctx.raw / total) * 100).toFixed(1);
                  return ctx.label + ': ' + ctx.raw + ' data (' + pct + '%)';
                }
              }
            }
          }
        }
      });
    }
  }

  // 2. BAR — Top 10 Emiten
  var topStocks = shTopStocks.value;
  if (topStocks && topStocks.length) {
    var ctx2 = document.getElementById('shTopStockChart');
    if (ctx2) {
      if (shTopStockChartInstance) { shTopStockChartInstance.destroy(); shTopStockChartInstance = null; }
      shTopStockChartInstance = new Chart(ctx2, {
        type: 'bar',
        data: {
          labels: topStocks.map(function(s) { return s.stock_code; }),
          datasets: [{
            label: 'Jumlah Holders',
            data: topStocks.map(function(s) { return s.holder_count; }),
            backgroundColor: accentLight,
            borderColor: accent,
            borderWidth: 1,
            borderRadius: 4,
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor, stepSize: 1 } },
            x: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } }
          }
        }
      });
    }
  }

  // 3. BAR HORIZONTAL — Top 10 Holders
  var topHolders = topShareholders.value;
  if (topHolders && topHolders.length) {
    var ctx3 = document.getElementById('shTopHolderChart');
    if (ctx3) {
      if (shTopHolderChartInstance) { shTopHolderChartInstance.destroy(); shTopHolderChartInstance = null; }
      var holders10 = topHolders.slice().sort(function(a,b) { return (b.total_pct||0) - (a.total_pct||0); }).slice(0, 10);
      shTopHolderChartInstance = new Chart(ctx3, {
        type: 'bar',
        data: {
          labels: holders10.map(function(h) {
            var n = h.shareholder_name || '';
            return n.length > 30 ? n.substring(0,28)+'...' : n;
          }),
          datasets: [{
            label: 'Total Kepemilikan %',
            data: holders10.map(function(h) { return parseFloat((h.total_pct||0).toFixed(2)); }),
            backgroundColor: holders10.map(function(h) {
              return (h.stock_count||0) > 20 ? 'rgba(239,68,68,0.7)' : 'rgba(124,58,237,0.7)';
            }),
            borderColor: holders10.map(function(h) {
              return (h.stock_count||0) > 20 ? '#EF4444' : '#7C3AED';
            }),
            borderWidth: 1, borderRadius: 4,
          }]
        },
        options: {
          indexAxis: 'y', responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                afterLabel: function(ctx) {
                  var item = holders10[ctx.dataIndex];
                  return 'Saham dipegang: ' + (item.stock_count||0) + ' emiten';
                }
              }
            }
          },
          scales: {
            x: { grid: { color: gridColor }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } },
            y: { grid: { display: false }, ticks: { color: textColor, font: { size: 9 } } }
          }
        }
      });
    }
  }
  renderScatterChart();
  renderHistogramChart();
  renderConcBucketChart();
  renderTopConcentratedChart();
  // Force re-render Top 10 Holders chart via nextTick chain
  window.Vue.nextTick(function() {
    var ch = document.getElementById('shTopHolderChart');
    if (ch && shTopHolderChartInstance) {
      shTopHolderChartInstance.resize();
    }
  });
}

var shStockDetailChartInstance = null;

function renderStockDetailChart() {
  var data = shStockResult.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  var sorted = data.slice().sort(function(a,b) { return (b.share_percent||0) - (a.share_percent||0); });
  var top15 = sorted.slice(0, 15);
  var labels = top15.map(function(s) {
    var n = s.shareholder_name || '';
    return n.length > 25 ? n.substring(0,23)+'...' : n;
  });
  var vals = top15.map(function(s) { return parseFloat((s.share_percent||0).toFixed(2)); });

  var ctx = document.getElementById('shStockDetailChart');
  if (!ctx) return;
  if (shStockDetailChartInstance) { shStockDetailChartInstance.destroy(); shStockDetailChartInstance = null; }
  shStockDetailChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '% Kepemilikan',
        data: vals,
        backgroundColor: vals.map(function(v) { return v >= 5 ? 'rgba(239,68,68,0.7)' : 'rgba(124,58,237,0.6)'; }),
        borderColor: vals.map(function(v) { return v >= 5 ? '#EF4444' : '#7C3AED'; }),
        borderWidth: 1, borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } },
        y: { grid: { display: false }, ticks: { color: textColor, font: { size: 9 } } }
      }
    }
  });
}

var shHolderPortfolioChartInstance = null;

function renderHolderPortfolioChart() {
  var data = shHolderResult.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';

  var sorted = data.slice().sort(function(a,b) { return (b.share_percent||0) - (a.share_percent||0); }).slice(0, 15);
  var labels = sorted.map(function(s) { return s.stock_code; });
  var vals = sorted.map(function(s) { return parseFloat((s.share_percent||0).toFixed(2)); });

  var ctx = document.getElementById('shHolderPortfolioChart');
  if (!ctx) return;
  if (shHolderPortfolioChartInstance) { shHolderPortfolioChartInstance.destroy(); shHolderPortfolioChartInstance = null; }
  shHolderPortfolioChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '% Kepemilikan',
        data: vals,
        backgroundColor: 'rgba(16,185,129,0.6)',
        borderColor: '#10B981',
        borderWidth: 1, borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(0,0,0,0.05)' }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } },
        y: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } }
      }
    }
  });
}

var shScatterChartInstance = null;

function renderScatterChart() {
  var data = shScatterData.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  var canvas = document.getElementById('bubbleChart');
  if (!canvas) return;
  if (shScatterChartInstance) { shScatterChartInstance.destroy(); shScatterChartInstance = null; }

  var ctx = canvas.getContext('2d');

  function makeDataset(label, stocks, color) {
    return {
      label: label + ' (' + stocks.length + ')',
      data: stocks.map(function(s) { return { x: s.holders, y: s.top_pct, stock: s.stock_code, total: s.total_pct }; }),
      backgroundColor: color,
      borderColor: color.replace('0.6','1').replace('0.5','1'),
      borderWidth: 0.3,
      pointRadius: 5,
      pointHoverRadius: 8,
    };
  }

  var highConc = [], medConc = [], lowConc = [];
  data.forEach(function(s) {
    if (s.top_pct >= 50) highConc.push(s);
    else if (s.top_pct >= 20) medConc.push(s);
    else lowConc.push(s);
  });

  shScatterChartInstance = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        makeDataset('≥50% Sangat Terkonsentrasi', highConc, 'rgba(239,68,68,0.7)'),
        makeDataset('20-50% Terkonsentrasi', medConc, 'rgba(245,158,11,0.7)'),
        makeDataset('<20% Tersebar', lowConc, 'rgba(59,130,246,0.6)'),
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 0 },
      plugins: {
        legend: {
          position: 'top',
          labels: { color: textColor, font: { size: 10 }, boxWidth: 14, padding: 10, usePointStyle: true }
        },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              var d = ctx.raw;
              return d.stock + ': top ' + d.y.toFixed(1) + '%, ' + d.x + ' holders, ' + d.total.toFixed(1) + '% total';
            }
          }
        }
      },
      scales: {
        x: {
          type: 'logarithmic',
          title: { display: true, text: 'Jumlah Pemegang Saham (log)', color: textColor },
          min: 0.5,
          grid: { color: gridColor },
          ticks: { color: textColor, callback: function(v) { var n = Math.round(v); return n > 0 ? n : ''; } }
        },
        y: {
          title: { display: true, text: 'Kepemilikan Terbesar (%)', color: textColor },
          min: 0, max: 100,
          grid: { color: gridColor },
          ticks: { color: textColor, callback: function(v) { return v + '%'; } }
        }
      }
    }
  });
}

var shHistogramChartInstance = null;

function renderHistogramChart() {
  var data = shScatterData.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  var canvas = document.getElementById('shHistogramChart');
  if (!canvas) return;
  if (shHistogramChartInstance) { shHistogramChartInstance.destroy(); shHistogramChartInstance = null; }

  var buckets = { '1':0,'2':0,'3':0,'4':0,'5':0,'6-10':0,'11-20':0,'21+':0 };
  data.forEach(function(s) {
    var h = s.holders;
    if (h === 1) buckets['1']++;
    else if (h === 2) buckets['2']++;
    else if (h === 3) buckets['3']++;
    else if (h === 4) buckets['4']++;
    else if (h === 5) buckets['5']++;
    else if (h <= 10) buckets['6-10']++;
    else if (h <= 20) buckets['11-20']++;
    else buckets['21+']++;
  });

  var labels = Object.keys(buckets);
  var vals = labels.map(function(k) { return buckets[k]; });

  shHistogramChartInstance = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Jumlah Emiten',
        data: vals,
        backgroundColor: vals.map(function(v) {
          if (v >= 100) return 'rgba(239,68,68,0.7)';
          if (v >= 50) return 'rgba(245,158,11,0.7)';
          return 'rgba(59,130,246,0.6)';
        }),
        borderColor: 'transparent',
        borderRadius: 3,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } },
        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } }
      }
    }
  });
}

var shConcBucketChartInstance = null;

function renderConcBucketChart() {
  var data = shScatterData.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  var canvas = document.getElementById('shConcentrationBucketChart');
  if (!canvas) return;
  if (shConcBucketChartInstance) { shConcBucketChartInstance.destroy(); shConcBucketChartInstance = null; }

  var buckets = {};
  for (var i = 0; i <= 90; i += 10) buckets[i + '-' + (i+10)] = 0;
  buckets['0-10'] = 0;

  data.forEach(function(s) {
    var p = s.top_pct;
    if (p < 10) buckets['0-10']++;
    else if (p < 20) buckets['10-20']++;
    else if (p < 30) buckets['20-30']++;
    else if (p < 40) buckets['30-40']++;
    else if (p < 50) buckets['40-50']++;
    else if (p < 60) buckets['50-60']++;
    else if (p < 70) buckets['60-70']++;
    else if (p < 80) buckets['70-80']++;
    else if (p < 90) buckets['80-90']++;
    else buckets['90-100']++;
  });

  var labels = Object.keys(buckets);
  var vals = labels.map(function(k) { return buckets[k]; });

  shConcBucketChartInstance = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Jumlah Emiten',
        data: vals,
        backgroundColor: vals.map(function(v, i) {
          if (i >= 7) return 'rgba(239,68,68,0.7)';
          if (i >= 4) return 'rgba(245,158,11,0.7)';
          return 'rgba(59,130,246,0.6)';
        }),
        borderColor: 'transparent',
        borderRadius: 3,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { color: textColor, font: { size: 9 }, maxRotation: 45 } },
        y: { beginAtZero: true, grid: { color: gridColor }, ticks: { color: textColor } }
      }
    }
  });
}

var shTopConcentratedChartInstance = null;

function renderTopConcentratedChart() {
  var data = shScatterData.value;
  if (!data || !data.length) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  var textColor = isDark ? '#aaa' : '#666';
  var gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';

  var canvas = document.getElementById('shTopConcentratedChart');
  if (!canvas) return;
  if (shTopConcentratedChartInstance) { shTopConcentratedChartInstance.destroy(); shTopConcentratedChartInstance = null; }

  var top10 = data.slice().sort(function(a,b) { return b.top_pct - a.top_pct; }).slice(0, 10);

  shTopConcentratedChartInstance = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: top10.map(function(s) { return s.stock_code; }),
      datasets: [{
        label: 'Kepemilikan Terbesar (%)',
        data: top10.map(function(s) { return s.top_pct; }),
        backgroundColor: 'rgba(239,68,68,0.7)',
        borderColor: '#EF4444',
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      indexAxis: 'y', responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: function(ctx) {
              var item = top10[ctx.dataIndex];
              return 'Pemegang: ' + item.holders + ' | Total: ' + item.total_pct.toFixed(1) + '%';
            }
          }
        }
      },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor, callback: function(v) { return v + '%'; } } },
        y: { grid: { display: false }, ticks: { color: textColor, font: { size: 10 } } }
      }
    }
  });
}
