# Chart Template Snippets for Quick Implementation

## Basic Chart Section (Add before referrals/records section)

```html
<!-- Charts Row -->
<div class="row mb-4">
    <!-- Daily Trend Chart -->
    <div class="col-xl-8 col-lg-7 mb-4">
        <div class="card shadow h-100">
            <div class="card-header py-3">
                <h6 class="m-0 font-weight-bold text-primary">Daily Volume (Last 7 Days)</h6>
            </div>
            <div class="card-body">
                <canvas id="dailyTrendChart" height="80"></canvas>
            </div>
        </div>
    </div>

    <!-- Status Distribution Chart -->
    <div class="col-xl-4 col-lg-5 mb-4">
        <div class="card shadow h-100">
            <div class="card-header py-3">
                <h6 class="m-0 font-weight-bold text-primary">Status Distribution</h6>
            </div>
            <div class="card-body">
                <canvas id="statusChart" height="200"></canvas>
            </div>
        </div>
    </div>
</div>
```

## Chart.js Scripts (Add in {% block extra_js %})

```html
{% block extra_js %}
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

<script>
    // Daily Trend Chart
    const dailyTrendCtx = document.getElementById('dailyTrendChart').getContext('2d');
    new Chart(dailyTrendCtx, {
        type: 'line',
        data: {
            labels: {{ daily_trend.labels|safe }},
            datasets: [{
                label: 'Records',
                data: {{ daily_trend.data|safe }},
                borderColor: '#4e73df',
                backgroundColor: 'rgba(78, 115, 223, 0.05)',
                borderWidth: 2,
                pointRadius: 4,
                fill: true,
                tension: 0.3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top' }
            },
            scales: {
                y: { beginAtZero: true, ticks: { precision: 0 } }
            }
        }
    });

    // Status Distribution Chart
    const statusCtx = document.getElementById('statusChart').getContext('2d');
    new Chart(statusCtx, {
        type: 'doughnut',
        data: {
            labels: {{ status_distribution.labels|safe }},
            datasets: [{
                data: {{ status_distribution.data|safe }},
                backgroundColor: {{ status_distribution.colors|safe }},
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            let value = context.parsed || 0;
                            let total = context.dataset.data.reduce((a, b) => a + b, 0);
                            let percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return label + ': ' + value + ' (' + percentage + '%)';
                        }
                    }
                }
            }
        }
    });
</script>
{% endblock %}
```

## Enhanced Stat Card with Trend

```html
<div class="col-xl-3 col-md-6 mb-4">
    <div class="card border-left-primary shadow h-100 py-2">
        <div class="card-body">
            <div class="row no-gutters align-items-center">
                <div class="col mr-2">
                    <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">
                        Total Records
                    </div>
                    <div class="h5 mb-0 font-weight-bold text-gray-800">
                        {{ total_records }}
                        {% if performance.trend_direction == 'up' %}
                            <small class="text-success ml-2">
                                <i class="fas fa-arrow-up"></i> {{ performance.trend_percentage }}%
                            </small>
                        {% elif performance.trend_direction == 'down' %}
                            <small class="text-danger ml-2">
                                <i class="fas fa-arrow-down"></i> {{ performance.trend_percentage }}%
                            </small>
                        {% endif %}
                    </div>
                </div>
                <div class="col-auto">
                    <i class="fas fa-clipboard-list fa-2x text-gray-300"></i>
                </div>
            </div>
        </div>
    </div>
</div>
```

