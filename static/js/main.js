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

    // Add Medication Item
    $('#add-medication-item').click(function() {
        var formsetContainer = $('#medication-items-container');
        var totalForms = $('#id_form-TOTAL_FORMS');
        var formIndex = parseInt(totalForms.val());

        var emptyFormTemplate = $('#empty-form-template').html();
        var newFormHtml = emptyFormTemplate.replace(/__prefix__/g, formIndex);
        var newForm = $(newFormHtml);

        newForm.find('input, textarea').val(''); // Clear values
        newForm.find('select').val('').trigger('change'); // Clear selected option and trigger change for Select2
        newForm.find('.select2-container').remove(); // Remove old Select2 instance

        formsetContainer.append(newForm);
        initializeSelect2(newForm.find('select')); // Initialize Select2 on the new select

        totalForms.val(formIndex + 1);
    });
});
