/**
 * Dashboard Auto-Update - Poll for analysis completion
 */

class DashboardAutoUpdate {
    constructor() {
        this.pollingInterval = 3000; // Check every 3 seconds
        this.pollerIds = {};
        this.init();
    }

    /**
     * Initialize polling for all processing analyses
     */
    init() {
        // Find all processing analyses on the dashboard
        const processingCards = document.querySelectorAll('[data-analysis-id][data-analysis-status]');
        
        processingCards.forEach(card => {
            const analysisId = card.dataset.analysisId;
            const status = card.dataset.analysisStatus?.toLowerCase().trim();
            
            if (status === 'processing') {
                console.log(`🔄 Starting polling for analysis ${analysisId}`);
                this.startPolling(analysisId, card);
            }
        });
    }

    /**
     * Start polling for a specific analysis
     */
    startPolling(analysisId, card) {
        if (this.pollerIds[analysisId]) {
            clearInterval(this.pollerIds[analysisId]);
        }

        this.pollerIds[analysisId] = setInterval(async () => {
            await this.checkStatus(analysisId, card);
        }, this.pollingInterval);
    }

    /**
     * Stop polling for a specific analysis
     */
    stopPolling(analysisId) {
        if (this.pollerIds[analysisId]) {
            clearInterval(this.pollerIds[analysisId]);
            delete this.pollerIds[analysisId];
            console.log(`⏹️ Stopped polling for analysis ${analysisId}`);
        }
    }

    /**
     * Check analysis status
     */
    async checkStatus(analysisId, card) {
        try {
            const response = await fetch(`/api/analysis/${analysisId}`, {
                credentials: 'include'
            });

            if (!response.ok) return;

            const analysis = await response.json();
            this.handleStatusUpdate(analysisId, card, analysis);

        } catch (error) {
            console.error(`❌ Polling error for analysis ${analysisId}:`, error);
        }
    }

    /**
     * Handle status updates
     */
    handleStatusUpdate(analysisId, card, analysis) {
        const statusBadge = card.querySelector('[data-analysis-status]');
        const currentStatus = statusBadge?.textContent?.toLowerCase().trim();

        // If status changed from "processing" to "completed"
        if (currentStatus === 'processing' && analysis.status === 'completed') {
            console.log(`✅ Analysis ${analysisId} completed!`);
            
            // Update status badge
            this.updateStatusBadge(statusBadge, analysis.status);
            
            // Update scores if they exist
            this.updateScores(card, analysis);
            
            // Show action buttons
            this.updateActionButtons(card, analysis);
            
            // Show notification
            Utils.showNotification(`✅ Analysis #${analysisId} completed!`, 'success');
            
            // Stop polling
            this.stopPolling(analysisId);
        }
    }

    /**
     * Update status badge
     */
    updateStatusBadge(badge, status) {
        badge.textContent = status.toUpperCase();
        badge.className = 'badge badge-success';
        badge.dataset.analysisStatus = status;
    }

    /**
     * Update score displays
     */
    updateScores(card, analysis) {
        const scoresGrid = card.querySelector('.scores-grid');
        if (!scoresGrid) return;

        // Update SEO score
        const seoScore = analysis.seo_overall_score || 0;
        const seoBar = scoresGrid.querySelector('[data-score-type="seo"]');
        if (seoBar) {
            seoBar.dataset.score = seoScore;
            seoBar.textContent = seoScore;
            this.updateScoreColor(seoBar, seoScore);
            seoBar.style.width = seoScore + '%';
        }

        // Update UX score
        const uxScore = analysis.ux_overall_score || 0;
        const uxBar = scoresGrid.querySelector('[data-score-type="ux"]');
        if (uxBar) {
            uxBar.dataset.score = uxScore;
            uxBar.textContent = uxScore;
            this.updateScoreColor(uxBar, uxScore);
            uxBar.style.width = uxScore + '%';
        }

        // Show scores grid
        scoresGrid.style.display = 'grid';
    }

    /**
     * Update score color based on value
     */
    updateScoreColor(element, score) {
        element.className = 'progress-bar';
        if (score >= 80) {
            element.classList.add('success');
        } else if (score >= 60) {
            element.classList.add('warning');
        } else {
            element.classList.add('danger');
        }
    }

    /**
     * Update action buttons
     */
    updateActionButtons(card, analysis) {
        const footer = card.querySelector('.card-footer');
        if (!footer) return;

        // Remove existing "View Details" button if present
        const existingBtn = footer.querySelector('a[href*="/analysis/"]');
        if (!existingBtn && analysis.status === 'completed') {
            const viewBtn = document.createElement('a');
            viewBtn.href = `/analysis/${analysis.id}`;
            viewBtn.className = 'btn btn-secondary btn-sm';
            viewBtn.textContent = '📊 View Details';
            footer.insertAdjacentElement('afterbegin', viewBtn);
        }
    }
}

/**
 * Initialize on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('📱 Dashboard loaded, starting auto-update monitoring...');
    window.dashboardAutoUpdate = new DashboardAutoUpdate();
});