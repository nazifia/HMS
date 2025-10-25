# 📋 Template Enhancement Guide

## 🎯 **Overview**

All 13 department dashboard views have been enhanced with comprehensive metrics and chart data. Now the templates need to be updated to display these features using Chart.js.

---

## 📊 **What Needs to Be Done**

Each of the 13 department dashboard templates needs:

1. **Chart.js CDN** - Add Chart.js library
2. **Chart Containers** - Add canvas elements for charts
3. **Chart Initialization** - Add JavaScript to create charts
4. **Enhanced Stat Cards** - Add trend indicators to statistics
5. **Urgent Items Section** - Display priority/emergency cases (where applicable)
6. **Active Staff Section** - Show staff active in last 24 hours

---

## 📁 **Templates to Update**

| # | Template Path | Department |
|---|---------------|------------|
| 1 | `templates/laboratory/dashboard.html` | Laboratory |
| 2 | `templates/radiology/dashboard.html` | Radiology |
| 3 | `templates/dental/dashboard.html` | Dental |
| 4 | `templates/icu/dashboard.html` | ICU |
| 5 | `templates/anc/dashboard.html` | ANC |
| 6 | `templates/labor/dashboard.html` | Labor |
| 7 | `templates/scbu/dashboard.html` | SCBU |
| 8 | `templates/ophthalmic/dashboard.html` | Ophthalmic |
| 9 | `templates/ent/dashboard.html` | ENT |
| 10 | `templates/oncology/dashboard.html` | Oncology |
| 11 | `templates/family_planning/dashboard.html` | Family Planning |
| 12 | `templates/gynae_emergency/dashboard.html` | Gynae Emergency |
| 13 | `templates/theatre/dashboard.html` | Theatre |

---

## 🔧 **Implementation Pattern**

### **Step 1: Add Chart.js CDN**

Add this in the template's extra CSS/JS block or at the bottom before `</body>`:

```html
{% block extra_js %}
{{ block.super }}
<!-- Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{% endblock %}
```

---

### **Step 2: Add Chart Containers**

Add canvas elements where you want charts to appear:

```html
<!-- Daily Trend Chart -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">Daily Trend (Last 7 Days)</h5>
    </div>
    <div class="card-body">
        <canvas id="dailyTrendChart" height="80"></canvas>
    </div>
</div>

<!-- Status Distribution Chart -->
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">Status Distribution</h5>
    </div>
    <div class="card-body">
        <canvas id="statusChart" height="80"></canvas>
    </div>
</div>
```

---

### **Step 3: Initialize Charts**

Add JavaScript to create charts using data from the backend:

```html
<script>
// Daily Trend Chart (Line Chart)
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
            legend: {
                display: true,
                position: 'top'
            },
            tooltip: {
                mode: 'index',
                intersect: false
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    precision: 0
                }
            }
        }
    }
});

// Status Distribution Chart (Doughnut Chart)
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
            legend: {
                position: 'right'
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        let label = context.label || '';
                        let value = context.parsed || 0;
                        let total = context.dataset.data.reduce((a, b) => a + b, 0);
                        let percentage = ((value / total) * 100).toFixed(1);
                        return label + ': ' + value + ' (' + percentage + '%)';
                    }
                }
            }
        }
    }
});
</script>
```

---

### **Step 4: Enhanced Stat Cards with Trends**

Update statistics cards to show trend indicators:

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
                            <small class="text-success">
                                <i class="fas fa-arrow-up"></i> {{ performance.trend_percentage }}%
                            </small>
                        {% elif performance.trend_direction == 'down' %}
                            <small class="text-danger">
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

---

### **Step 5: Urgent Items Section**

Add a section to display urgent/priority items (if applicable):

```html
{% if urgent_items %}
<div class="card mb-4">
    <div class="card-header bg-danger text-white">
        <h5 class="mb-0">
            <i class="fas fa-exclamation-triangle"></i> Urgent Items
        </h5>
    </div>
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Patient</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Date</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in urgent_items %}
                    <tr>
                        <td>{{ item.patient.get_full_name }}</td>
                        <td>
                            <span class="badge badge-danger">{{ item.priority|upper }}</span>
                        </td>
                        <td>{{ item.status }}</td>
                        <td>{{ item.created_at|date:"M d, Y" }}</td>
                        <td>
                            <a href="#" class="btn btn-sm btn-primary">View</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endif %}
```

---

### **Step 6: Active Staff Section**

Add a section to show active staff:

```html
{% if active_staff %}
<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0">
            <i class="fas fa-user-md"></i> Active Staff (Last 24 Hours)
        </h5>
    </div>
    <div class="card-body">
        <div class="row">
            {% for staff in active_staff %}
            <div class="col-md-4 mb-3">
                <div class="d-flex align-items-center">
                    <div class="mr-3">
                        <div class="icon-circle bg-success">
                            <i class="fas fa-user text-white"></i>
                        </div>
                    </div>
                    <div>
                        <div class="font-weight-bold">{{ staff.user.get_full_name }}</div>
                        <div class="text-muted small">{{ staff.user.profile.specialization|default:"Staff" }}</div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endif %}
```

---

## 📊 **Department-Specific Charts**

### **Laboratory**
- Daily trend (line chart)
- Status distribution (doughnut chart)
- Priority distribution (doughnut chart)

### **Radiology**
- Daily imaging volume (line chart)
- Status distribution (doughnut chart)
- Modality distribution (bar chart)

### **Dental**
- Daily patient volume (line chart)
- Treatment status (doughnut chart)
- Popular procedures (bar chart)

### **ICU**
- Daily admissions/discharges (line chart)
- GCS severity distribution (doughnut chart)
- Equipment usage (bar chart)

### **ANC**
- Daily visit volume (line chart)
- Trimester distribution (doughnut chart)

### **Labor**
- Daily delivery volume (line chart)
- Delivery mode distribution (doughnut chart)

### **SCBU**
- Daily admissions (line chart)
- Condition severity (doughnut chart)

### **Ophthalmic**
- Daily visit volume (line chart)
- Diagnosis distribution (bar chart)

### **ENT**
- Daily visit volume (line chart)
- Diagnosis distribution (bar chart)

### **Oncology**
- Daily visit volume (line chart)
- Cancer type distribution (bar chart)
- Stage distribution (doughnut chart)

### **Family Planning**
- Daily visit volume (line chart)
- Contraceptive method distribution (doughnut chart)

### **Gynae Emergency**
- Daily emergency volume (line chart)
- Triage distribution (doughnut chart)
- Emergency type distribution (bar chart)

### **Theatre**
- Daily surgery volume (line chart)
- Surgery type distribution (bar chart)
- Status distribution (doughnut chart)

---

## ✅ **Checklist for Each Template**

- [ ] Add Chart.js CDN
- [ ] Add daily trend chart container and initialization
- [ ] Add status distribution chart container and initialization
- [ ] Add department-specific chart(s) container and initialization
- [ ] Update stat cards with trend indicators
- [ ] Add urgent items section (if applicable)
- [ ] Add active staff section
- [ ] Test chart rendering
- [ ] Test responsive design
- [ ] Verify data accuracy

---

## 🎨 **Styling Tips**

1. **Card Heights**: Use `height="80"` on canvas elements for consistent sizing
2. **Colors**: Use consistent color schemes across charts
3. **Responsive**: Charts are responsive by default with Chart.js
4. **Icons**: Use Font Awesome icons for visual appeal
5. **Spacing**: Use Bootstrap spacing utilities (mb-4, py-2, etc.)

---

## 🚀 **Quick Start**

1. Choose a template to enhance
2. Copy the reference implementation from `templates/laboratory/enhanced_dashboard.html`
3. Adjust chart types and data based on department-specific metrics
4. Test the dashboard
5. Move to the next template

---

**Estimated Time per Template:** 15-20 minutes  
**Total Estimated Time:** 3-4 hours for all 13 templates

