/**
 * Main app initialization
 */

class App {
    constructor() {
        this.init();
    }

    /**
     * Initialize app
     */
    init() {
        console.log('🚀 Initializing App...');

        // Load theme preference
        this.loadTheme();

        // Initialize global error handler
        this.setupErrorHandler();

        // Log environment
        console.log('✅ App initialized');
    }

    /**
     * Load theme preference
     */
    loadTheme() {
        const theme = StorageService.preferences.getTheme();
        document.documentElement.setAttribute('data-theme', theme);
    }

    /**
     * Setup global error handler
     */
    setupErrorHandler() {
        window.addEventListener('error', (event) => {
            console.error('Global error:', event.error);
        });

        window.addEventListener('unhandledrejection', (event) => {
            console.error('Unhandled rejection:', event.reason);
        });
    }
    
}

// Set progress bar widths from data attribute
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.progress-bar[data-score]').forEach((bar) => {
        const score = bar.dataset.score;
        bar.style.setProperty('--score-width', `${score}%`);
    });
});

// Initialize app
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new App();
    });
} else {
    new App();
}