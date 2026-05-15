/**
 * Auth Page Logic - Login and Register
 */

class AuthApp {
    constructor() {
        this.form = document.querySelector('.auth-form') || document.querySelector('form');
        this.submitBtn = this.form?.querySelector('button[type="submit"]');
        this.init();
    }

    /**
     * Initialize auth app
     */
    init() {
        if (!this.form) return;

        this.setupEventListeners();
        this.focusFirstInput();
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e));

        // Real-time validation
        const inputs = this.form.querySelectorAll('input');
        inputs.forEach((input) => {
            input.addEventListener('blur', () => this.validateField(input));
        });
    }

    /**
     * Handle form submission
     */
    async handleSubmit(e) {
        e.preventDefault();

        // Validate all fields
        const inputs = this.form.querySelectorAll('input');
        let isValid = true;
        inputs.forEach((input) => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });

        if (!isValid) return;

        // Show loading state
        Utils.setLoading(this.submitBtn, true);

        try {
            console.log('🔐 Submitting auth form...');

            // Submit form (let backend handle it)
            this.form.submit();
        } catch (error) {
            console.error('❌ Error:', error);
            Utils.showNotification('An error occurred', 'error');
            Utils.setLoading(this.submitBtn, false);
        }
    }

    /**
     * Validate individual field
     */
    validateField(input) {
        const value = input.value.trim();
        const type = input.getAttribute('type') || input.getAttribute('name');
        let isValid = true;

        // Clear previous error
        const errorEl = input.nextElementSibling;
        if (errorEl?.classList.contains('form-error')) {
            errorEl.remove();
        }

        // Validation rules
        if (!value) {
            this.showError(input, 'This field is required');
            isValid = false;
        } else if (type === 'email') {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                this.showError(input, 'Please enter a valid email');
                isValid = false;
            }
        } else if (type === 'password') {
            if (value.length < 6) {
                this.showError(input, 'Password must be at least 6 characters');
                isValid = false;
            }
        } else if (type === 'username') {
            if (value.length < 3) {
                this.showError(input, 'Username must be at least 3 characters');
                isValid = false;
            }
        }

        return isValid;
    }

    /**
     * Show error message
     */
    showError(input, message) {
        const error = document.createElement('div');
        error.className = 'form-error';
        error.textContent = message;
        input.parentElement.insertBefore(error, input.nextElementSibling);
        input.classList.add('is-invalid');
    }

    /**
     * Focus first input
     */
    focusFirstInput() {
        const firstInput = this.form?.querySelector('input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new AuthApp();
    });
} else {
    new AuthApp();
}