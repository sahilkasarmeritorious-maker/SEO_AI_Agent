/**
 * Markdown rendering with syntax highlighting
 */

class MarkdownRenderer {
    constructor() {
        this.init();
    }

    /**
     * Initialize markdown rendering
     */
    init() {
        // Wait for marked and highlight.js to load
        if (typeof marked === 'undefined' || typeof hljs === 'undefined') {
            console.warn('⚠️ Marked or Highlight.js not loaded');
            return;
        }

        // Configure marked
        marked.setOptions({
            breaks: true,
            gfm: true,
            pedantic: false,
        });

        // Render all markdown content
        this.renderAll();

        // Watch for new messages
        const observer = new MutationObserver(() => this.renderAll());
        const messages = document.querySelector('.chat-messages');
        if (messages) {
            observer.observe(messages, { childList: true });
        }
    }

    /**
     * Render all markdown responses
     */
    renderAll() {
        document.querySelectorAll('.assistant-response').forEach((el) => {
            if (el.dataset.rendered) return; // Skip already rendered

            const text = el.textContent.trim();
            if (!text) return;

            try {
                // Parse markdown
                const html = marked.parse(text);

                // Create wrapper
                const wrapper = document.createElement('div');
                wrapper.className = 'markdown-content';
                wrapper.innerHTML = html;

                // Highlight code blocks
                wrapper.querySelectorAll('pre code').forEach((code) => {
                    try {
                        hljs.highlightElement(code);
                    } catch (error) {
                        console.warn('Syntax highlighting error:', error);
                    }
                });

                // Replace content
                el.innerHTML = '';
                el.appendChild(wrapper);
                el.dataset.rendered = 'true';

                console.log('✨ Markdown rendered');
            } catch (error) {
                console.error('Markdown rendering error:', error);
            }
        });
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        new MarkdownRenderer();
    });
} else {
    new MarkdownRenderer();
}