/* static/js/script.js */

document.addEventListener('DOMContentLoaded', function() {
    console.log("Bus Pass System Frontend Initialized.");

    // --- Basic Client-Side Validation for Registration Form ---
    const registerForm = document.querySelector('form[action*="/register"]');
    if (registerForm) {
        registerForm.addEventListener('submit', function(event) {
            const password = document.getElementById('password').value;
            const phone = document.getElementById('phone_number').value;

            // Simple Password Length Check
            if (password.length < 6) {
                alert("Password must be at least 6 characters long.");
                event.preventDefault(); // Stop form submission
                return;
            }

            // Simple Phone Number Format Check (e.g., 10 digits)
            // Checks if it's purely digits and between 10-15 characters long
            if (!/^\d{10,15}$/.test(phone)) {
                alert("Please enter a valid phone number (10-15 digits only).");
                event.preventDefault();
                return;
            }

            console.log("Registration form validated successfully (client-side).");
        });
    }

    // --- Dynamic Payment Button Text ---
    const paymentForm = document.querySelector('form[action*="/payment"]');
    if (paymentForm) {
        paymentForm.addEventListener('submit', function(event) {
            // Check if payment is successful before preventing default
            const payButton = paymentForm.querySelector('.button.primary');
            if (payButton) {
                // In a real scenario, this would initiate a call to the payment gateway
                payButton.textContent = "Processing Payment...";
                payButton.disabled = true;
            }
            // Allow form submission to proceed to the backend simulation
        });
    }

    // --- Route Selection Check (Preventing same start/end point) ---
    const applyPassForm = document.querySelector('form[action*="/apply_pass"]');
    if (applyPassForm) {
        applyPassForm.addEventListener('submit', function(event) {
            const startPoint = document.querySelector('select[name="start_point"]').value;
            const endPoint = document.querySelector('select[name="end_point"]').value;

            if (startPoint === endPoint) {
                alert("Start point and Destination point cannot be the same. Please select a valid route.");
                event.preventDefault();
            }
        });
    }
});
