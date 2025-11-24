// Patient search functionality for all medical modules
// This script handles AJAX requests to search for patients and populate select fields

document.addEventListener('DOMContentLoaded', function() {
    // Handle patient search inputs across all medical modules
    const patientSearchInputs = document.querySelectorAll('.patient-search');
    
    patientSearchInputs.forEach(function(searchInput) {
        // Create search results container
        const resultsContainer = document.createElement('div');
        resultsContainer.className = 'patient-search-results dropdown-menu';
        resultsContainer.style.display = 'none';
        resultsContainer.style.position = 'absolute';
        resultsContainer.style.zIndex = '1000';
        resultsContainer.style.maxHeight = '300px';
        resultsContainer.style.overflowY = 'auto';
        resultsContainer.style.width = '100%';
        
        // Insert results container after the search input
        searchInput.parentNode.style.position = 'relative';
        searchInput.parentNode.insertBefore(resultsContainer, searchInput.nextSibling);
        
        let searchTimeout;
        
        // Handle input event for patient search
        searchInput.addEventListener('input', function() {
            const query = this.value.trim();
            const selectField = searchInput.closest('form').querySelector('.patient-select');
            
            // Clear previous timeout
            clearTimeout(searchTimeout);
            
            // If query is empty, hide results and reset select
            if (query.length === 0) {
                resultsContainer.style.display = 'none';
                if (selectField) {
                    selectField.value = '';
                }
                return;
            }
            
            // Show loading state
            resultsContainer.innerHTML = '<div class="dropdown-item">Searching...</div>';
            resultsContainer.style.display = 'block';
            
            // Debounce search requests
            searchTimeout = setTimeout(() => {
                searchPatients(query, resultsContainer, selectField);
            }, 150);
        });
        
        // Hide results when clicking outside
        document.addEventListener('click', function(e) {
            if (!searchInput.contains(e.target) && !resultsContainer.contains(e.target)) {
                resultsContainer.style.display = 'none';
            }
        });
    });
});

function searchPatients(query, resultsContainer, selectField) {
    // In a real implementation, this would make an AJAX request to the server
    // For now, we'll simulate the search with a mock API call
    
    // Example AJAX request (uncomment and modify for your actual API):
    /*
    fetch(`/api/patients/search/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            displayPatientResults(data, resultsContainer, selectField);
        })
        .catch(error => {
            console.error('Error searching patients:', error);
            resultsContainer.innerHTML = '<div class="dropdown-item text-danger">Error searching patients</div>';
        });
    */
    
    // Mock implementation for demonstration
    // In a real application, replace this with actual AJAX call to your backend
    mockPatientSearch(query, resultsContainer, selectField);
}

function mockPatientSearch(query, resultsContainer, selectField) {
    // This is a mock implementation for demonstration purposes
    // In a real application, this would be replaced with an actual AJAX call
    
    // Simulate API delay
    setTimeout(() => {
        // Mock patient data - in a real app this would come from the server
        const mockPatients = [
            {id: 1, name: 'John Doe', patient_id: 'P001', phone: '123-456-7890'},
            {id: 2, name: 'Jane Smith', patient_id: 'P002', phone: '098-765-4321'},
            {id: 3, name: 'Robert Johnson', patient_id: 'P003', phone: '555-123-4567'},
            {id: 4, name: 'Emily Davis', patient_id: 'P004', phone: '444-987-6543'},
            {id: 5, name: 'Michael Wilson', patient_id: 'P005', phone: '333-654-0987'}
        ];
        
        // Filter mock data based on query
        const filteredPatients = mockPatients.filter(patient => 
            patient.name.toLowerCase().includes(query.toLowerCase()) ||
            patient.patient_id.toLowerCase().includes(query.toLowerCase()) ||
            patient.phone.includes(query)
        );
        
        displayPatientResults(filteredPatients, resultsContainer, selectField);
    }, 200);
}

function displayPatientResults(patients, resultsContainer, selectField) {
    // Clear previous results
    resultsContainer.innerHTML = '';
    
    if (patients.length === 0) {
        resultsContainer.innerHTML = '<div class="dropdown-item text-muted">No patients found</div>';
        resultsContainer.style.display = 'block';
        return;
    }
    
    // Add each patient to the results
    patients.forEach(patient => {
        const item = document.createElement('div');
        item.className = 'dropdown-item patient-result-item';
        item.style.cursor = 'pointer';
        item.innerHTML = `
            <div>
                <strong>${patient.name}</strong>
                <small class="text-muted d-block">ID: ${patient.patient_id} | Phone: ${patient.phone}</small>
            </div>
        `;
        
        // Handle click on patient result
        item.addEventListener('click', function() {
            // Update search input with selected patient
            const searchInput = resultsContainer.previousElementSibling;
            searchInput.value = `${patient.name} (${patient.patient_id})`;
            
            // Update select field with patient ID
            if (selectField) {
                selectField.value = patient.id;
                
                // Trigger change event to notify any listeners
                const event = new Event('change', { bubbles: true });
                selectField.dispatchEvent(event);
            }
            
            // Hide results
            resultsContainer.style.display = 'none';
        });
        
        resultsContainer.appendChild(item);
    });
    
    // Show results
    resultsContainer.style.display = 'block';
}

// Initialize patient search when the page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPatientSearch);
} else {
    initPatientSearch();
}

function initPatientSearch() {
    // Any additional initialization code can go here
    console.log('Patient search functionality initialized');
}