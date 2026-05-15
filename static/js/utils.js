/**
 * Utility functions - common helpers
 */

const Utils = {
    /**
     * Debounce function to prevent rapid function calls
     */
    debounce(func, delay = 300) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    },

    /**
     * Throttle function
     */
    throttle(func, delay = 300) {
        let lastCall = 0;
        return function (...args) {
            const now = Date.now();
            if (now - lastCall >= delay) {
                lastCall = now;
                func.apply(this, args);
            }
        };
    },

    /**
     * Format date to readable string
     */
    formatDate(date) {
        const d = new Date(date);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (d.toDateString() === today.toDateString()) {
            return d.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
            });
        } else if (d.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        }
        return d.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
        });
    },

    /**
     * Truncate text to max length
     */
    truncate(text, maxLength = 50) {
        if (text.length <= maxLength) return text;
        const truncated = text.substring(0, maxLength);
        const lastSpace = truncated.lastIndexOf(' ');
        return (lastSpace > 0 ? truncated.substring(0, lastSpace) : truncated) + '...';
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;',
        };
        return text.replace(/[&<>"']/g, (char) => map[char]);
    },

    /**
     * Deep clone object
     */
    clone(obj) {
        return JSON.parse(JSON.stringify(obj));
    },

    /**
     * Check if element is in viewport
     */
    isInViewport(element) {
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    },

    /**
     * Show notification toast
     */
    showNotification(message, type = 'success', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `alert alert-${type}`;
        toast.textContent = message;
        toast.style.position = 'fixed';
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        toast.style.minWidth = '300px';

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 200ms';
            setTimeout(() => toast.remove(), 200);
        }, duration);
    },

    /**
     * Get URL parameters
     */
    getUrlParam(name) {
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    },

    /**
     * Update URL without reload
     */
    updateUrl(url) {
        window.history.pushState({}, '', url);
    },

    /**
     * Smooth scroll to element
     */
    scrollTo(element, behavior = 'smooth') {
        if (element) {
            element.scrollIntoView({ behavior });
        }
    },

    /**
     * Loading animation
     */
    setLoading(button, isLoading) {
        const originalText = button.dataset.originalText || button.innerHTML;

        if (isLoading) {
            button.dataset.originalText = originalText;
            button.innerHTML = '⏳ Processing...';
            button.disabled = true;
            button.classList.add('btn-loading');
        } else {
            button.innerHTML = originalText;
            button.disabled = false;
            button.classList.remove('btn-loading');
        }
    },
};