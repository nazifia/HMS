#!/usr/bin/env python
"""
Script to add Chart.js integration to all department dashboard templates
This script adds chart sections and initialization scripts to dashboard templates
"""

import os
import re

# Chart HTML template to insert
CHART_SECTION = '''
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
'''

# Chart.js script template
CHART_SCRIPT = '''
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
'''

# Departments to update
DEPARTMENTS = [
    'laboratory',
    'icu',
    'anc',
    'labor',
    'scbu',
    'ophthalmic',
    'ent',
    'oncology',
    'family_planning',
    'gynae_emergency'
]

def update_template(template_path):
    """
    Update a dashboard template with chart sections
    """
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return False
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if charts are already added
    if 'dailyTrendChart' in content:
        print(f"Charts already added to {template_path}")
        return False
    
    # Find the location to insert charts (before referrals section or recent records)
    # Look for common patterns
    patterns = [
        r'(<div class="row">\s*<!-- Pending Referrals Section -->)',
        r'(<div class="row">\s*<div class="col-lg-6 mb-4">\s*<div class="card shadow mb-4">)',
        r'(<div class="row">\s*<!-- Recent Records -->)',
    ]
    
    inserted = False
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            # Insert chart section before the match
            content = content[:match.start()] + CHART_SECTION + '\n' + content[match.start():]
            inserted = True
            break
    
    if not inserted:
        print(f"Could not find insertion point in {template_path}")
        return False
    
    # Add Chart.js script at the end if not already present
    if '{% block extra_js %}' not in content:
        # Add before {% endblock %} at the end
        content = content.rstrip()
        if content.endswith('{% endblock %}'):
            content = content[:-len('{% endblock %}')] + CHART_SCRIPT
        else:
            content += '\n' + CHART_SCRIPT
    
    # Write updated content
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Successfully updated {template_path}")
    return True

def main():
    """
    Main function to update all department templates
    """
    base_path = 'templates'
    updated_count = 0
    
    for dept in DEPARTMENTS:
        template_path = os.path.join(base_path, dept, 'dashboard.html')
        if update_template(template_path):
            updated_count += 1
    
    print(f"\nUpdated {updated_count} out of {len(DEPARTMENTS)} templates")

if __name__ == '__main__':
    main()

