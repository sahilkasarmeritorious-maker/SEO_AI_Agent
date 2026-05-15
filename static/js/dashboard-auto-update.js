/**
 * Dashboard Auto-Update - Poll for analysis completion
 */

class DashboardAutoUpdate {
    constructor() {
        this.pollingInterval = 9000; // Check every 9 seconds
        this.pollerIds = {};
        this.init();
    }

    /**
     * Initialize polling for all processing analyses
     */
    init() {
        // Find all processing analyses on the dashboard
        const processingCards = document.querySelectorAll('[data-analysis-id][data-analysis-status]');
        
        console.log(`🔍 Found ${processingCards.length} analysis cards`);
        
        processingCards.forEach(card => {
            const analysisId = card.dataset.analysisId;
            const status = card.dataset.analysisStatus?.toLowerCase().trim();
            
            console.log(`  - Analysis ${analysisId}: ${status}`);
            
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

            if (!response.ok) {
                console.log(`⚠️ Analysis ${analysisId} still processing...`);
                return;
            }

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

        console.log(`📊 Analysis ${analysisId}: ${currentStatus} -> ${analysis.status}`);

        // If status changed from "processing" to "completed"
        if (currentStatus === 'processing' && analysis.status === 'completed') {
            console.log(`✅ Analysis ${analysisId} completed!`);
            
            // Update status badge
            this.updateStatusBadge(statusBadge, analysis.status);
            
            // Update scores if they exist
            this.updateScores(card, analysis);
            
            // Update action buttons
            this.updateActionButtons(card, analysis);
            
            // Show notification
            Utils.showNotification(`✅ Analysis completed!`, 'success');
            
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
        
        // If scores grid doesn't exist, we need to add it
        if (!scoresGrid) {
            console.log('📊 Creating scores grid...');
            this.createScoresGrid(card, analysis);
            return;
        }

        // Update SEO score
        const seoScore = analysis.seo_overall_score || 0;
        const seoBar = scoresGrid.querySelector('[data-score-type="seo"]');
        if (seoBar) {
            seoBar.dataset.score = seoScore;
            seoBar.textContent = seoScore + '%';
            this.updateScoreColor(seoBar, seoScore);
            seoBar.style.width = seoScore + '%';
        }

        // Update UX score
        const uxScore = analysis.ux_overall_score || 0;
        const uxBar = scoresGrid.querySelector('[data-score-type="ux"]');
        if (uxBar) {
            uxBar.dataset.score = uxScore;
            uxBar.textContent = uxScore + '%';
            this.updateScoreColor(uxBar, uxScore);
            uxBar.style.width = uxScore + '%';
        }

        // Show scores grid
        scoresGrid.style.display = 'grid';
        console.log('✅ Scores updated');
    }

        /**
         * Create scores grid if it doesn't exist
         */
        createScoresGrid(card, analysis) {
            const processingIndicator = card.querySelector('.processing-indicator');
            
            const scoresHtml = `
                <div class="scores-grid">
                    <div class="score-item">
                        <label class="score-label">SEO Score</label>
                        <div class="progress">
                            <div 
                                class="progress-bar ${this.getScoreClass(analysis.seo_overall_score)}" 
                                data-score-type="seo"
                                data-score="${analysis.seo_overall_score}"
                                style="width: ${analysis.seo_overall_score}%"
                            >
                                ${analysis.seo_overall_score}%
                            </div>
                        </div>
                    </div>
        
                    <div class="score-item">
                        <label class="score-label">UX Score</label>
                        <div class="progress">
                            <div 
                                class="progress-bar ${this.getScoreClass(analysis.ux_overall_score)}" 
                                data-score-type="ux"
                                data-score="${analysis.ux_overall_score}"
                                style="width: ${analysis.ux_overall_score}%"
                            >
                                ${analysis.ux_overall_score}%
                            </div>
                        </div>
                    </div>
                </div>
            `;
        
            if (processingIndicator) {
                // Use insertAdjacentHTML to properly parse HTML
                processingIndicator.insertAdjacentHTML('beforebegin', scoresHtml);
                processingIndicator.remove();
                console.log('✅ Scores grid created and displayed');
            }
        }

    /**
     * Get score class based on value
     */
    getScoreClass(score) {
        if (score >= 80) {
            return 'success';
        } else if (score >= 60) {
            return 'warning';
        } else {
            return 'danger';
        }
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

        // Check if "View Details" button already exists
        const existingBtn = footer.querySelector('a[href*="/analysis/"]');
        if (!existingBtn && analysis.id) {
            const viewBtn = document.createElement('a');
            viewBtn.href = `/analysis/${analysis.id}`;
            viewBtn.className = 'btn btn-secondary btn-sm';
            viewBtn.innerHTML = '📊 View Details';
            footer.insertAdjacentElement('afterbegin', viewBtn);
            console.log('✅ Added View Details button');
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