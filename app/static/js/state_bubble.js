// state_bubble.js - Bubble Chart Logic
function renderBubbleChart(data) {
    const ctx = document.getElementById('bubbleChart').getContext('2d');
    new Chart(ctx, {
        type: 'bubble',
        data: {
            datasets: [{
                label: 'Market Concentration',
                data: data.map(item => ({
                    x: item.market_cap,
                    y: item.volatility,
                    r: item.holding_size / 1000000 
                })),
                backgroundColor: 'rgba(54, 162, 235, 0.5)'
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: true } }
        }
    });
}
