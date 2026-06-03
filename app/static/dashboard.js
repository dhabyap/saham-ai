let mainChart = null;
let rsiChart = null;
let macdChart = null;
let volumeChart = null;
let currentCode = null;
let currentPeriod = '3mo';
let allStocks = [];

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadStocks();
    setupPeriodButtons();
    setupSidebarToggle();
});

function setupSidebarToggle() {
    document.getElementById('sidebarToggle').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('collapsed');
    });
}

function setupPeriodButtons() {
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPeriod = btn.dataset.period;
            if (currentCode) loadStockData(currentCode);
        });
    });
}

async function loadStocks() {
    try {
        const res = await fetch('/api/stocks');
        const data = await res.json();
        allStocks = data.stocks || [];
        renderStocks(allStocks);
    } catch (e) {
        document.getElementById('stockList').innerHTML = '<div class="text-center text-danger py-3">Error loading stocks</div>';
    }
}

function renderStocks(stocks) {
    const container = document.getElementById('stockList');
    container.innerHTML = stocks.map(s => `
        <div class="stock-item" onclick="selectStock('${s.code}')" data-code="${s.code}">
            <span class="stock-code">${s.code}</span>
            <span class="stock-change" id="change-${s.code}">-</span>
        </div>
    `).join('');

    // Fetch changes for all stocks
    stocks.forEach(s => fetchStockChange(s.code));
}

function filterStocks(query) {
    const filtered = allStocks.filter(s =>
        s.code.toLowerCase().includes(query.toLowerCase()) ||
        s.name.toLowerCase().includes(query.toLowerCase())
    );
    renderStocks(filtered);
}

async function fetchStockChange(code) {
    try {
        const res = await fetch(`/api/stock/${code}?period=5d`);
        const data = await res.json();
        if (data.change_pct !== undefined) {
            const el = document.getElementById(`change-${code}`);
            if (el) {
                const pct = data.change_pct;
                el.textContent = (pct > 0 ? '+' : '') + pct.toFixed(2) + '%';
                el.className = 'stock-change ' + (pct >= 0 ? 'positive' : 'negative');
            }
        }
    } catch (e) {}
}

async function selectStock(code) {
    currentCode = code;

    // Highlight active
    document.querySelectorAll('.stock-item').forEach(el => el.classList.remove('active'));
    const activeEl = document.querySelector(`.stock-item[data-code="${code}"]`);
    if (activeEl) activeEl.classList.add('active');

    document.getElementById('currentStock').textContent = code;
    loadStockData(code);
}

async function loadStockData(code) {
    try {
        const res = await fetch(`/api/analyze/${code}?period=${currentPeriod}`);
        const data = await res.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        updateSummaryCards(data);
        updateAnalysisPanel(data);
        renderMainChart(data);
        renderRsiChart(data);
        renderMacdChart(data);
        renderVolumeChart(data);
    } catch (e) {
        showError('Error loading data');
    }
}

function updateSummaryCards(data) {
    document.getElementById('cardPrice').textContent = 'Rp' + formatNumber(data.price);

    const change = data.change_pct || 0;
    const changeEl = document.getElementById('cardChange');
    changeEl.textContent = (change > 0 ? '+' : '') + change.toFixed(2) + '%';
    changeEl.className = change >= 0 ? 'text-success' : 'text-danger';

    document.getElementById('cardRsi').textContent = data.rsi || '-';
    const rsiStatus = document.getElementById('cardRsiStatus');
    rsiStatus.textContent = data.rsi_status || '-';
    if (data.rsi_status === 'Overbought') rsiStatus.className = 'text-danger';
    else if (data.rsi_status === 'Oversold') rsiStatus.className = 'text-success';
    else rsiStatus.className = 'text-muted';

    document.getElementById('cardMacd').textContent = data.macd ? data.macd.toFixed(2) : '-';
    document.getElementById('cardMacdStatus').textContent = data.macd_status || '-';

    const rec = data.recommendation || '-';
    const recEl = document.getElementById('cardRec');
    recEl.textContent = rec;
    if (rec === 'BUY') recEl.className = 'mb-0 text-success';
    else if (rec === 'SELL') recEl.className = 'mb-0 text-danger';
    else recEl.className = 'mb-0 text-warning';

    document.getElementById('cardConf').textContent = 'Confidence: ' + (data.confidence || '-') + '%';
}

function updateAnalysisPanel(data) {
    const panel = document.getElementById('analysisPanel');
    const recClass = data.recommendation === 'BUY' ? 'rec-buy' :
                     data.recommendation === 'SELL' ? 'rec-sell' : 'rec-hold';

    panel.innerHTML = `
        <div class="analysis-item">
            <span class="analysis-label">Trend</span>
            <span class="analysis-value">${data.trend || '-'}</span>
        </div>
        <div class="analysis-item">
            <span class="analysis-label">RSI</span>
            <span class="analysis-value">${data.rsi || '-'} (${data.rsi_status || '-'})</span>
        </div>
        <div class="analysis-item">
            <span class="analysis-label">MACD</span>
            <span class="analysis-value">${data.macd_status || '-'}</span>
        </div>
        <div class="analysis-item">
            <span class="analysis-label">MA20</span>
            <span class="analysis-value">Rp${formatNumber(data.ma20)}</span>
        </div>
        <div class="analysis-item">
            <span class="analysis-label">MA50</span>
            <span class="analysis-value">Rp${formatNumber(data.ma50)}</span>
        </div>
        <div class="analysis-item">
            <span class="analysis-label">Support</span>
            <span class="analysis-value text-success">Rp${formatNumber(data.support)}</span>
        </div>
        <div class="analysis-item">
            <span class="analysis-label">Resistance</span>
            <span class="analysis-value text-danger">Rp${formatNumber(data.resistance)}</span>
        </div>
        <div class="analysis-item">
            <span class="analysis-label">Volume</span>
            <span class="analysis-value">${formatVolume(data.volume)}</span>
        </div>
        <div class="mt-3 p-2 rounded" style="background:#1a1d23">
            <div class="fw-bold ${recClass}">${data.recommendation} (${data.confidence || 0}%)</div>
            <small class="text-muted mt-1 d-block">${data.reason || ''}</small>
        </div>
    `;
}

function renderMainChart(data) {
    const ctx = document.getElementById('mainChart').getContext('2d');

    if (mainChart) mainChart.destroy();

    if (!data.history || data.history.length === 0) {
        mainChart = new Chart(ctx, {
            type: 'line',
            data: { datasets: [] },
            options: { responsive: true, maintainAspectRatio: false }
        });
        return;
    }

    const labels = data.history.map(h => h.date?.substring(0, 10));
    const closes = data.history.map(h => h.close);
    const ma20 = data.history.map(h => h.ma20);
    const ma50 = data.history.map(h => h.ma50);

    mainChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Close',
                    data: closes,
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13,110,253,0.1)',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                    borderWidth: 2,
                },
                {
                    label: 'MA20',
                    data: ma20,
                    borderColor: '#f59e0b',
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.2,
                },
                {
                    label: 'MA50',
                    data: ma50,
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    pointRadius: 0,
                    tension: 0.2,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { boxWidth: 12, padding: 8, font: { size: 10 } }
                }
            },
            scales: {
                x: {
                    ticks: { maxTicksLimit: 10, font: { size: 9 }, color: '#888' },
                    grid: { display: false }
                },
                y: {
                    ticks: { font: { size: 9 }, color: '#888' },
                    grid: { color: '#222' }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function renderRsiChart(data) {
    const ctx = document.getElementById('rsiChart').getContext('2d');
    if (rsiChart) rsiChart.destroy();

    if (!data.history || data.history.length === 0) {
        rsiChart = new Chart(ctx, { type: 'line', data: { datasets: [] } });
        return;
    }

    const labels = data.history.map(h => h.date?.substring(0, 10));
    const rsi = data.history.map(h => h.rsi);

    rsiChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'RSI',
                    data: rsi,
                    borderColor: '#a855f7',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    tension: 0.3,
                },
                {
                    label: 'Overbought',
                    data: Array(labels.length).fill(70),
                    borderColor: '#ef4444',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                },
                {
                    label: 'Oversold',
                    data: Array(labels.length).fill(30),
                    borderColor: '#22c55e',
                    borderWidth: 1,
                    borderDash: [5, 5],
                    pointRadius: 0,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { min: 0, max: 100, ticks: { font: { size: 8 }, color: '#888' }, grid: { color: '#222' } },
                x: { display: false }
            }
        }
    });
}

function renderMacdChart(data) {
    const ctx = document.getElementById('macdChart').getContext('2d');
    if (macdChart) macdChart.destroy();

    if (!data.history || data.history.length === 0) {
        macdChart = new Chart(ctx, { type: 'line', data: { datasets: [] } });
        return;
    }

    // We don't have MACD per item in history, so use a simplified view
    const labels = data.history.map(h => h.date?.substring(0, 10));
    const closes = data.history.map(h => h.close);

    // Simple MACD approximation for display
    const ema12 = calculateEMA(closes, 12);
    const ema26 = calculateEMA(closes, 26);
    const macdLine = ema12.map((v, i) => v - ema26[i]);
    const signal = calculateEMA(macdLine, 9);
    const hist = macdLine.map((v, i) => v - signal[i]);

    macdChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'MACD',
                    data: macdLine,
                    borderColor: '#3b82f6',
                    backgroundColor: 'transparent',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    type: 'line',
                    order: 1,
                },
                {
                    label: 'Signal',
                    data: signal,
                    borderColor: '#ef4444',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    type: 'line',
                    order: 1,
                },
                {
                    label: 'Histogram',
                    data: hist,
                    backgroundColor: hist.map(v => v >= 0 ? 'rgba(34,197,94,0.6)' : 'rgba(239,68,68,0.6)'),
                    order: 0,
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { ticks: { font: { size: 8 }, color: '#888' }, grid: { color: '#222' } },
                x: { display: false }
            }
        }
    });
}

function renderVolumeChart(data) {
    const ctx = document.getElementById('volumeChart').getContext('2d');
    if (volumeChart) volumeChart.destroy();

    if (!data.history || data.history.length === 0) {
        volumeChart = new Chart(ctx, { type: 'bar', data: { datasets: [] } });
        return;
    }

    const labels = data.history.map(h => h.date?.substring(0, 10));
    const volumes = data.history.map(h => h.volume);

    volumeChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Volume',
                data: volumes,
                backgroundColor: volumes.map((v, i) => {
                    if (i === 0) return 'rgba(13,110,253,0.5)';
                    return v > volumes[i-1] ? 'rgba(34,197,94,0.5)' : 'rgba(239,68,68,0.5)';
                }),
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { ticks: { font: { size: 8 }, color: '#888' }, grid: { color: '#222' } },
                x: { display: false }
            }
        }
    });
}

// Helper Functions
function formatNumber(num) {
    if (num === null || num === undefined) return '-';
    return Number(num).toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatVolume(vol) {
    if (!vol) return '-';
    if (vol >= 1e9) return (vol / 1e9).toFixed(2) + 'B';
    if (vol >= 1e6) return (vol / 1e6).toFixed(2) + 'M';
    if (vol >= 1e3) return (vol / 1e3).toFixed(0) + 'K';
    return vol.toString();
}

function calculateEMA(data, period) {
    const k = 2 / (period + 1);
    const ema = [data[0]];
    for (let i = 1; i < data.length; i++) {
        ema.push(data[i] * k + ema[i-1] * (1 - k));
    }
    return ema;
}

function showError(msg) {
    console.error(msg);
}
