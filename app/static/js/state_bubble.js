// state_bubble.js - Bubble Chart Logic
function renderBubbleChart(dominantStocks) {
    console.log("Rendering chart with:", dominantStocks);
    const canvas = document.getElementById('bubbleChart');
    if (!canvas) return;
    
    // Destroy existing chart if exists
    if (window.myBubbleChart) window.myBubbleChart.destroy();

    const ctx = canvas.getContext('2d');
    window.myBubbleChart = new Chart(ctx, {
        type: 'bubble',
        data: {
            datasets: [{
                label: 'Market Concentration',
                data: dominantStocks.map(s => ({
                    x: s.total_owned_pct,
                    y: s.holder_count * 5, 
                    r: s.top_holder_pct / 2
                })),
                backgroundColor: 'rgba(147, 51, 234, 0.6)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // FEB2026 adalah periode valid
    fetch('/api/shareholders/concentration?period=FEB2026')
        .then(res => res.json())
        .then(data => {
            if (data.dominant_stocks && data.dominant_stocks.length > 0) {
                renderBubbleChart(data.dominant_stocks);
            } else {
                console.warn("No dominant stocks data found.");
            }
        })
        .catch(err => console.error("Error loading bubble data:", err));
});