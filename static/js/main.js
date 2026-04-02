// Arasan EV CRM JavaScript

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Confirm delete actions
function confirmDelete(message = 'Are you sure you want to delete this item?') {
    return confirm(message);
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

// Auto-submit forms on filter change
document.addEventListener('DOMContentLoaded', function() {
    const filterSelects = document.querySelectorAll('.filter-row');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            this.closest('form').submit();
        });
    });
});

// Search functionality
document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('.search-bar input');
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                this.closest('form').submit();
            }, 500);
        });
    });
});

// Vehicle price API
function loadVehiclePrice(vehicleId, targetElement) {
    if (!vehicleId) return;
    
    fetch(`/api/vehicle-price/${vehicleId}`)
        .then(response => response.json())
        .then(data => {
            if (data.price) {
                targetElement.textContent = formatCurrency(data.price);
            }
        })
        .catch(error => console.error('Error loading vehicle price:', error));
}

// Initialize tooltips or other UI enhancements
document.addEventListener('DOMContentLoaded', function() {
    // Add any initialization code here
    console.log('Arasan EV CRM loaded');
});