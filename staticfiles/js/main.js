// Custom JavaScript for Hospital Management System

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        $('.alert').alert('close');
    }, 5000);

    // Appointment date picker enhancement
    if (document.getElementById('appointment-date')) {
        flatpickr('#appointment-date', {
            enableTime: true,
            dateFormat: "Y-m-d H:i",
            minDate: "today",
            time_24hr: true
        });
    }

    // Patient search functionality
    $('#patient-search').on('keyup', function() {
        var value = $(this).val().toLowerCase();
        $('#patient-table tbody tr').filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1);
        });
    });

    // Confirm delete modals
    $('.delete-confirm').on('click', function(e) {
        e.preventDefault();
        var targetUrl = $(this).attr('href');
        
        $('#confirmDeleteModal').modal('show');
        $('#confirmDeleteBtn').on('click', function() {
            window.location.href = targetUrl;
        });
    });

    // Print functionality
    $('.print-btn').on('click', function() {
        window.print();
    });

    // Chart.js initialization for dashboard
    if (document.getElementById('patientsChart')) {
        var ctx = document.getElementById('patientsChart').getContext('2d');
        var myChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                datasets: [{
                    label: 'New Patients',
                    data: [12, 19, 3, 5, 2, 3, 10, 15, 8, 12, 5, 7],
                    backgroundColor: 'rgba(0, 123, 255, 0.2)',
                    borderColor: 'rgba(0, 123, 255, 1)',
                    borderWidth: 2,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Prescription form dynamic fields
    if (document.getElementById('add-medication')) {
        document.getElementById('add-medication').addEventListener('click', function() {
            var medicationFields = document.getElementById('medication-fields');
            var newRow = document.createElement('div');
            newRow.className = 'row medication-row mb-3';
            newRow.innerHTML = `
                <div class="col-md-5">
                    <select class="form-select" name="medication[]" required>
                        <option value="">Select Medication</option>
                        <!-- Options will be populated dynamically -->
                    </select>
                </div>
                <div class="col-md-3">
                    <input type="text" class="form-control" name="dosage[]" placeholder="Dosage" required>
                </div>
                <div class="col-md-3">
                    <input type="text" class="form-control" name="frequency[]" placeholder="Frequency" required>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-danger remove-medication">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            medicationFields.appendChild(newRow);
            
            // Add event listener to the remove button
            newRow.querySelector('.remove-medication').addEventListener('click', function() {
                medicationFields.removeChild(newRow);
            });
            
            // Populate medication options via AJAX
            fetch('/pharmacy/api/medications/')
                .then(response => response.json())
                .then(data => {
                    var select = newRow.querySelector('select');
                    data.forEach(med => {
                        var option = document.createElement('option');
                        option.value = med.id;
                        option.textContent = med.name;
                        select.appendChild(option);
                    });
                });
        });
    }
});
