// Enhanced patient search functionality for desk office
document.addEventListener('DOMContentLoaded', function() {
    const patientSearchInput = document.getElementById('patient-search');
    
    if (patientSearchInput) {
        // For authorization dashboard, don't interfere with form submission
        // The form should work normally without AJAX intervention
        console.log('Patient search input found');
    }
    
    // Service type dependent fields
    const serviceTypeSelect = document.getElementById('id_service_type');
    if (serviceTypeSelect) {
        serviceTypeSelect.addEventListener('change', function() {
            const selectedValue = this.value;
            const descriptionField = document.getElementById('id_service_description');
            
            // Prefill description based on service type
            if (descriptionField) {
                switch(selectedValue) {
                    case 'laboratory':
                        descriptionField.placeholder = 'e.g., Complete Blood Count, Lipid Profile, etc.';
                        break;
                    case 'radiology':
                        descriptionField.placeholder = 'e.g., Chest X-Ray, CT Scan, MRI, etc.';
                        break;
                    case 'theatre':
                        descriptionField.placeholder = 'e.g., Appendectomy, C-Section, etc.';
                        break;
                    case 'dental':
                        descriptionField.placeholder = 'e.g., Cleaning, Extraction, Filling, etc.';
                        break;
                    case 'ent':
                        descriptionField.placeholder = 'e.g., Hearing Test, Tonsillectomy, etc.';
                        break;
                    default:
                        descriptionField.placeholder = 'Describe the specific service requested';
                }
            }
        });
    }
});