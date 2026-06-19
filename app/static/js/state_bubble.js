// state_bubble.js - Bubble Chart Logic
function renderBubbleChart(data) {
    if (!data || data.length === 0) {
        console.warn("Bubble chart data is empty");
        return;
    }
    const ctx = document.getElementById('bubbleChart').getContext('2d');
    
    // Fallback data if API returns weird structure
    const chartData = data.map(item => ({
        x: item.market_cap || 0,
        y: item.volatility || 0,
        r: (item.holding_size || 1000000) / 100000 
    }));

    new Chart(ctx, {
        type: 'bubble',
        data: {
            datasets: [{
                label: 'Market Concentration',
                data: chartData,
                backgroundColor: 'rgba(147, 51, 234, 0.5)' // Matching purple theme
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// Ensure data fetch triggers on page load
document.addEventListener('DOMContentLoaded', () => {
    // Ambil period dari state global (atau default)
    const period = document.getElementById('period-select')?.value || '2026-02'; 
    fetch(`/api/shareholders/concentration?period=${period}`)
        .then(res => res.json())
        .then(data => renderBubbleChart(data))
        .catch(err => console.error("Error loading bubble data:", err));
});
