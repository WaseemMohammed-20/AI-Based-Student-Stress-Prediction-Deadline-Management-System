/**
 * Dashboard: fetch weekly workload and render color-coded Chart.js bar chart.
 * Bars colored by stress level: High Stress = red, Busy = yellow, Normal = green.
 */
(function () {
    var canvas = document.getElementById('workloadChart');
    if (!canvas) return;

    var levelColors = {
        'High Stress': 'rgba(248, 81, 73, 0.7)',
        'Busy': 'rgba(210, 153, 34, 0.7)',
        'Normal': 'rgba(63, 185, 80, 0.6)'
    };

    fetch('/api/dashboard/chart')
        .then(function (res) { return res.json(); })
        .then(function (data) {
            var labels = data.labels || [];
            var values = data.data || [];
            var levels = data.levels || [];
            var colors = values.map(function (_, i) {
                var level = levels[i] || 'Normal';
                return levelColors[level] || levelColors['Normal'];
            });

            var ctx = canvas.getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Estimated hours',
                        data: values,
                        backgroundColor: colors,
                        borderColor: colors.map(function (c) {
                            return c.replace('0.7', '1').replace('0.6', '1');
                        }),
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { color: '#8b949e', font: { size: 11 } },
                            grid: { color: '#30363d' }
                        },
                        x: {
                            ticks: { color: '#8b949e', font: { size: 11 } },
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                afterLabel: function (ctx) {
                                    var level = levels[ctx.dataIndex];
                                    return level ? 'Stress: ' + level : '';
                                }
                            }
                        }
                    }
                }
            });
        })
        .catch(function () {
            if (canvas.parentElement) {
                canvas.parentElement.innerHTML = '<p class="muted">Could not load chart data.</p>';
            }
        });
})();
