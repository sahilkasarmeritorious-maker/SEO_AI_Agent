/**
 * Analytics Service - Track user interactions
 * Optional: Remove if not needed
 */

const AnalyticsService = {
    enabled: true, // Toggle analytics on/off
    events: [],

    /**
     * Track event
     */
    track(eventName, data = {}) {
        if (!this.enabled) return;

        const event = {
            name: eventName,
            timestamp: new Date().toISOString(),
            url: window.location.pathname,
            ...data,
        };

        this.events.push(event);
        console.log('📊 Event tracked:', event.name);

        // Send to backend if we have a lot of events
        if (this.events.length >= 10) {
            this.flush();
        }
    },

    /**
     * Track page view
     */
    trackPageView(page) {
        this.track('page_view', { page });
    },

    /**
     * Track user action
     */
    trackAction(action, label, value) {
        this.track('user_action', { action, label, value });
    },

    /**
     * Track chat message
     */
    trackChatMessage(sessionId) {
        this.track('chat_message', { session_id: sessionId });
    },

    /**
     * Track error
     */
    trackError(error) {
        this.track('error', {
            message: error.message,
            stack: error.stack,
        });
    },

    /**
     * Flush events to backend
     */
    async flush() {
        if (this.events.length === 0) return;

        try {
            // Optional: Send to analytics endpoint if you have one
            console.log('📤 Sending analytics:', this.events.length, 'events');
            this.events = [];
        } catch (error) {
            console.warn('Analytics flush error:', error);
        }
    },

    /**
     * Initialize analytics
     */
    init() {
        // Track page view on load
        this.trackPageView(window.location.pathname);

        // Flush on page unload
        window.addEventListener('beforeunload', () => this.flush());

        // Periodic flush
        setInterval(() => this.flush(), 60000); // Every minute

        console.log('📊 Analytics initialized');
    },
};

// Auto-initialize
AnalyticsService.init();