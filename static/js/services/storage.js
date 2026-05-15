/**
 * Storage service - Handle local storage operations
 */

const StorageService = {
    PREFIX: 'ai_agent_',

    /**
     * Set item in localStorage
     */
    set(key, value) {
        try {
            localStorage.setItem(
                this.PREFIX + key,
                typeof value === 'string' ? value : JSON.stringify(value)
            );
        } catch (error) {
            console.warn('Storage error:', error);
        }
    },

    /**
     * Get item from localStorage
     */
    get(key) {
        try {
            const value = localStorage.getItem(this.PREFIX + key);
            if (!value) return null;

            try {
                return JSON.parse(value);
            } catch {
                return value;
            }
        } catch (error) {
            console.warn('Storage error:', error);
            return null;
        }
    },

    /**
     * Remove item from localStorage
     */
    remove(key) {
        try {
            localStorage.removeItem(this.PREFIX + key);
        } catch (error) {
            console.warn('Storage error:', error);
        }
    },

    /**
     * Clear all items
     */
    clear() {
        try {
            Object.keys(localStorage)
                .filter((key) => key.startsWith(this.PREFIX))
                .forEach((key) => localStorage.removeItem(key));
        } catch (error) {
            console.warn('Storage error:', error);
        }
    },

    /**
     * User preferences
     */
    preferences: {
        setTheme(theme) {
            StorageService.set('theme', theme);
        },

        getTheme() {
            return StorageService.get('theme') || 'light';
        },

        setSidebarCollapsed(collapsed) {
            StorageService.set('sidebar_collapsed', collapsed);
        },

        isSidebarCollapsed() {
            return StorageService.get('sidebar_collapsed') === true;
        },
    },

    /**
     * Chat cache
     */
    chat: {
        setCurrentSession(sessionId) {
            StorageService.set('current_session', sessionId);
        },

        getCurrentSession() {
            return StorageService.get('current_session');
        },

        setDraftMessage(sessionId, message) {
            StorageService.set(`draft_${sessionId}`, message);
        },

        getDraftMessage(sessionId) {
            return StorageService.get(`draft_${sessionId}`);
        },

        clearDraftMessage(sessionId) {
            StorageService.remove(`draft_${sessionId}`);
        },
    },
};