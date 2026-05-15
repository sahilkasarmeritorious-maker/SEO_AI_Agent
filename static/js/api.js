/**
 * API wrapper - centralized API calls
 * All backend communication goes through here
 */

const API = {
    BASE_URL: '',
    TIMEOUT: 30000,

    /**
     * Generic fetch wrapper with error handling
     */
    async request(endpoint, options = {}) {
        const {
            method = 'GET',
            body = null,
            headers = {},
            timeout = this.TIMEOUT,
        } = options;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(`${this.BASE_URL}${endpoint}`, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    ...headers,
                },
                body: body ? JSON.stringify(body) : null,
                credentials: 'include',
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const error = await response.json().catch(() => ({
                    detail: `HTTP ${response.status}: ${response.statusText}`,
                }));
                throw new Error(error.detail || 'API request failed');
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);
            console.error('API Error:', error);
            throw error;
        }
    },

    /**
     * Chat API calls
     */
    chat: {
        async sendMessage(sessionId, message, analysisId = null) {
            try {
                const body = {
                    message: message,
                    session_id: sessionId,
                };
                
                if (analysisId) {
                    body.analysis_id = analysisId;
                }
            
                const response = await fetch('/api/chat/message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(body),
                    credentials: 'include',
                });
            
                if (!response.ok) {
                    const error = await response.json().catch(() => ({
                        detail: `HTTP ${response.status}`
                    }));
                    console.error('Chat error:', error);
                    throw new Error(error.detail || 'Failed to send message');
                }
            
                return response.ok;
            } catch (error) {
                console.error('Send message error:', error);
                throw error;
            }
        },

        async getSessions(analysisId = null) {
            const params = analysisId ? `?analysis_id=${analysisId}` : '';
            return this.request(`/api/chat/sessions${params}`);
        },

        async createSession(analysisId = null) {
            const params = analysisId ? `?analysis_id=${analysisId}` : '';
            return this.request(`/api/chat/sessions/new${params}`, {
                method: 'POST',
            });
        },

        async getMessages(sessionId) {
            return this.request(`/api/chat/sessions/${sessionId}/messages`);
        },

        async deleteSession(sessionId) {
            return this.request(`/api/chat/sessions/${sessionId}`, {
                method: 'DELETE',
            });
        },
    },

    /**
     * Auth API calls
     */
    auth: {
        async login(username, password) {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch('/login', {
                method: 'POST',
                body: formData,
            });

            return response.ok;
        },

        async register(username, email, password) {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('email', email);
            formData.append('password', password);

            const response = await fetch('/register', {
                method: 'POST',
                body: formData,
            });

            return response.ok;
        },

        async logout() {
            window.location.href = '/logout';
        },
    },

    /**
     * Analysis API calls
     */
    analysis: {
        async getHistory() {
            return this.request('/api/analysis/history?skip=0&limit=10');
        },

        async submit(url) {
            const formData = new FormData();
            formData.append('url', url);

            const response = await fetch('/dashboard', {
                method: 'POST',
                body: formData,
            });

            return response.ok;
        },

        async getResult(analysisId) {
            return this.request(`/api/analysis/results/${analysisId}`);
        },
    },
};