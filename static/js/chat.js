/**
 * Chat Page Logic - Real-time updates without page reload
 */

class ChatApp {
    constructor() {
        this.sessionId = Utils.getUrlParam('session_id');
        this.analysisId = Utils.getUrlParam('analysis_id');
        this.isProcessing = false;

        console.log('🔧 ChatApp initialized:');
        console.log('  - Session ID:', this.sessionId);
        console.log('  - Analysis ID:', this.analysisId);

        this.elements = {
            form: document.querySelector('.chat-input-form'),
            input: document.querySelector('input[name="message"]'),
            button: document.querySelector('.chat-input-form button'),
            messages: document.querySelector('.chat-messages'),
            sidebar: document.querySelector('.chat-sidebar'),
            sessionsList: document.querySelector('.sessions-list'),
        };

        this.init();
    }

    /**
     * Initialize chat app
     */
    init() {
        if (!this.elements.form) {
            console.warn('⚠️ Chat form not found');
            return;
        }

        this.setupEventListeners();
        this.loadDraftMessage();
        this.focusInput();
        console.log('✅ ChatApp initialized successfully');
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // ✅ INTERCEPT form submission with AJAX
        this.elements.form.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Auto-save draft on input
        if (this.elements.input) {
            this.elements.input.addEventListener(
                'input',
                Utils.debounce((e) => this.saveDraft(e.target.value), 500)
            );
        }

        // Scroll to bottom on new messages
        if (this.elements.messages) {
            const observer = new MutationObserver(() => this.scrollToBottom());
            observer.observe(this.elements.messages, { childList: true });
        }
    }

    /**
     * Handle form submission with AJAX
     */
    async handleSubmit(e) {
        e.preventDefault();

        const message = this.elements.input.value.trim();
        if (!message || this.isProcessing) {
            console.warn('⚠️ Empty message or already processing');
            return;
        }

        // Check session_id
        if (!this.sessionId) {
            console.error('❌ No session_id in URL!');
            Utils.showNotification('Session error: No session ID', 'error');
            return;
        }

        this.isProcessing = true;
        Utils.setLoading(this.elements.button, true);
        this.elements.input.disabled = true;

        try {
            console.log('📤 Sending message to session', this.sessionId);
            console.log('📝 Message:', message);

            // Send message via AJAX
            const formData = new FormData();
            formData.append('message', message);
            formData.append('session_id', this.sessionId);
            if (this.analysisId) {
                formData.append('analysis_id', this.analysisId);
            }

            const response = await fetch('/api/chat/send', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            console.log('📨 Response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Server error:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            console.log('✅ Message sent successfully!');

            // Clear input and draft
            this.elements.input.value = '';
            StorageService.chat.clearDraftMessage(this.sessionId);

            // ✅ Wait a bit for backend to process
            await new Promise(resolve => setTimeout(resolve, 500));

            // ✅ Fetch updated messages WITHOUT reloading page
            console.log('🔄 Fetching updated messages...');
            await this.fetchAndDisplayMessages();

            console.log('✅ Messages updated on UI');

        } catch (error) {
            console.error('❌ Error sending message:', error);
            Utils.showNotification(`Failed to send message: ${error.message}`, 'error');
        } finally {
            this.isProcessing = false;
            Utils.setLoading(this.elements.button, false);
            this.elements.input.disabled = false;
            this.focusInput();
        }
    }

    /**
     * Fetch and display messages WITHOUT page reload
     */
    async fetchAndDisplayMessages() {
        try {
            console.log('🔍 Fetching messages for session:', this.sessionId);

            const url = `/api/chat/sessions/${this.sessionId}/messages`;
            console.log('📍 Fetching from:', url);

            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include'  // ✅ Use cookies, not Authorization header
            });

            console.log('📨 Fetch response status:', response.status);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Fetch failed:', response.status, errorText);
                throw new Error(`Failed to fetch messages: ${response.status}`);
            }

            const messages = await response.json();
            console.log('📩 Full Response:', messages);  // ← ADD THIS
            console.log('📩 Received', messages.length, 'messages');

            if (!this.elements.messages) {
                console.error('❌ Messages container not found!');
                return;
            }

            // Clear existing messages
            this.elements.messages.innerHTML = '';
            console.log('🗑️ Cleared old messages');

            // Add each message to chat
            if (messages.length === 0) {
                console.log('ℹ️ No messages to display');
            }

            messages.forEach((msg, index) => {
                console.log(`📌 Adding message ${index + 1}/${messages.length}`);
                this.addMessageToChat(msg);
            });

            // Scroll to bottom
            this.scrollToBottom();
            console.log('✅ All messages displayed');

        } catch (error) {
            console.error('❌ Fetch error:', error);
            Utils.showNotification(`Failed to load messages: ${error.message}`, 'error');
        }
    }

    /**
     * Add a single message to the chat display
     */
    addMessageToChat(msg) {
        try {
            // User message
            const userDiv = document.createElement('div');
            userDiv.className = 'message user-message';
            userDiv.innerHTML = `
                <p><strong>You:</strong> ${this.escapeHtml(msg.user_message)}</p>
                ${msg.analysis_id ? `<small class="message-meta">📌 Analysis #${msg.analysis_id}</small>` : ''}
            `;
            this.elements.messages.appendChild(userDiv);
            console.log('✅ Added user message');

            // Assistant message
            const assistantDiv = document.createElement('div');
            assistantDiv.className = 'message assistant-message';
            assistantDiv.innerHTML = `
                <div class="assistant-header">🤖 Assistant</div>
                <div class="assistant-response">${msg.assistant_response}</div>
                ${msg.sources && msg.sources.length > 0 ? this.buildSourcesHtml(msg.sources) : ''}
            `;
            this.elements.messages.appendChild(assistantDiv);
            console.log('✅ Added assistant message');

            // Re-render markdown for new message
            if (window.markdownRenderer) {
                window.markdownRenderer.render();
            }

        } catch (error) {
            console.error('❌ Error adding message to UI:', error);
        }
    }

    /**
     * Build sources HTML
     */
    buildSourcesHtml(sources) {
        const sourcesHtml = sources.map(source => `
            <div class="source-item">
                <p><strong>Analysis #${source.analysis_id}</strong></p>
                <p class="source-url">${this.escapeHtml(source.url)}</p>
                <small>SEO: ${source.seo_score}/100 | UX: ${source.ux_score}/100 | ${Math.round(source.relevance_score * 100)}% match</small>
            </div>
        `).join('');

        return `
            <div class="sources">
                <strong>📌 Sources (${sources.length}):</strong>
                ${sourcesHtml}
            </div>
        `;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Save draft message to localStorage
     */
    saveDraft(message) {
        if (this.sessionId) {
            StorageService.chat.setDraftMessage(this.sessionId, message);
            console.log('💾 Draft saved');
        }
    }

    /**
     * Load draft message from localStorage
     */
    loadDraftMessage() {
        if (!this.sessionId || !this.elements.input) return;

        const draft = StorageService.chat.getDraftMessage(this.sessionId);
        if (draft) {
            this.elements.input.value = draft;
            this.focusInput();
            console.log('📝 Draft loaded:', draft.substring(0, 30) + '...');
        }
    }

    /**
     * Focus input field
     */
    focusInput() {
        setTimeout(() => this.elements.input?.focus(), 100);
    }

    /**
     * Scroll to bottom of messages
     */
    scrollToBottom() {
        if (this.elements.messages) {
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        }
    }
}

/**
 * Global delete session function
 */
window.deleteSession = async function(e, sessionId, analysisId = null) {
    e.preventDefault();
    e.stopPropagation();

    if (!confirm('🗑️ Delete this session? This cannot be undone.')) {
        return;
    }

    try {
        console.log('🗑️ Deleting session:', sessionId);
        
        const response = await fetch(`/api/chat/sessions/${sessionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to delete session');
        }

        console.log('✅ Session deleted');
        Utils.showNotification('Session deleted successfully', 'success');

        // Redirect after short delay
        const redirectUrl = analysisId
            ? `/chat?analysis_id=${analysisId}`
            : '/chat';
        
        setTimeout(() => {
            window.location.href = redirectUrl;
        }, 500);
    } catch (error) {
        console.error('❌ Delete error:', error);
        Utils.showNotification(`Failed to delete session: ${error.message}`, 'error');
    }
};

/**
 * Setup delete button listeners
 */
function setupDeleteButtons() {
    document.querySelectorAll('.session-delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const sessionId = btn.dataset.sessionId;
            const analysisId = btn.dataset.analysisId;
            deleteSession(e, parseInt(sessionId), analysisId === 'null' ? null : parseInt(analysisId));
        });
    });
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('📱 DOM loaded, initializing ChatApp...');
    
    // Initialize ChatApp
    if (document.querySelector('.chat-input-form')) {
        window.chatApp = new ChatApp();
    }
    
    // Setup delete buttons
    setupDeleteButtons();
});