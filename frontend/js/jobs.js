/**
 * Kwork AI PM - Jobs Module
 */
const Jobs = {
    currentPage: 1,
    perPage: 20,
    totalPages: 1,
    currentStatus: 'all',
    currentSearch: '',

    /**
     * Load jobs with filters
     */
    async loadJobs(params = {}) {
        const tableBody = document.getElementById('jobsTableBody');
        
        // Show loading
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center" style="padding: 40px;">
                    <div class="spinner" style="margin: 0 auto;"></div>
                    <div class="text-muted" style="margin-top: 12px;">Yuklanmoqda...</div>
                </td>
            </tr>
        `;

        try {
            const requestParams = {
                page: params.page || this.currentPage,
                per_page: this.perPage,
                status: params.status || this.currentStatus,
                search: params.search !== undefined ? params.search : this.currentSearch
            };

            // Remove 'all' status filter
            if (requestParams.status === 'all') {
                delete requestParams.status;
            }

            const response = await API.jobs.list(requestParams);
            
            this.currentPage = response.page;
            this.totalPages = response.total_pages;
            
            this.renderJobs(response.items);
            this.renderPagination(response);

        } catch (error) {
            console.error('Failed to load jobs:', error);
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center text-error" style="padding: 40px;">
                        Ma'lumotlarni yuklashda xatolik yuz berdi
                    </td>
                </tr>
            `;
        }
    },

    /**
     * Render jobs table
     */
    renderJobs(jobs) {
        const tableBody = document.getElementById('jobsTableBody');
        
        if (!jobs || jobs.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center" style="padding: 60px;">
                        <div class="empty-state">
                            <div class="empty-state-icon">📭</div>
                            <div class="empty-state-title">E'lonlar topilmadi</div>
                            <div class="empty-state-description">Filterlarni o'zgartirib ko'ring yoki yangi e'lonlar paydo bo'lishini kuting</div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = jobs.map(job => `
            <tr data-job-id="${job.id}">
                <td class="job-title-cell">
                    <div class="job-title">${Dashboard.escapeHtml(job.title)}</div>
                    <div class="job-category">${job.category || 'Kategoriya yo\'q'}</div>
                </td>
                <td>
                    <span class="job-budget">${job.budget || '—'}</span>
                </td>
                <td>
                    ${Dashboard.getStatusBadge(job.status)}
                </td>
                <td>
                    ${Dashboard.getScoreDisplay(job.confidence_score)}
                </td>
                <td>
                    ${this.getRiskDisplay(job.risk_score)}
                </td>
                <td>
                    ${job.telegram_sent 
                        ? '<span class="badge badge-success">✓ Yuborildi</span>' 
                        : '<span class="badge badge-default">—</span>'}
                </td>
                <td>
                    <span class="job-time">${Dashboard.formatTime(job.created_at)}</span>
                </td>
                <td>
                    <div class="job-actions">
                        <button class="job-action-btn view" title="Ko'rish" onclick="Jobs.viewJob(${job.id})">
                            👁️
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    },

    /**
     * Get risk display
     */
    getRiskDisplay(score) {
        if (score === null || score === undefined) {
            return '<span class="text-muted">—</span>';
        }
        
        const percentage = Math.round(score * 100);
        let colorClass = 'high'; // high risk = red
        if (score <= 0.3) colorClass = 'high'; // low risk = green (inverted logic for display)
        else if (score <= 0.65) colorClass = 'medium';
        else colorClass = 'low';

        // Invert for visual: low risk should be green
        if (score <= 0.3) colorClass = 'high';
        else if (score <= 0.65) colorClass = 'medium';
        else colorClass = 'low';

        return `
            <div class="job-score">
                <div class="score-bar">
                    <div class="score-fill ${colorClass}" style="width: ${percentage}%"></div>
                </div>
                <span>${percentage}%</span>
            </div>
        `;
    },

    /**
     * Render pagination
     */
    renderPagination(data) {
        const info = document.getElementById('paginationInfo');
        const controls = document.getElementById('paginationControls');
        
        const start = (data.page - 1) * data.per_page + 1;
        const end = Math.min(data.page * data.per_page, data.total);
        
        info.textContent = `${data.total} ta e'londan ${start}-${end}`;

        let html = '';
        
        // Previous button
        html += `
            <button class="pagination-btn" ${data.page <= 1 ? 'disabled' : ''} onclick="Jobs.goToPage(${data.page - 1})">
                ←
            </button>
        `;

        // Page numbers
        const maxButtons = 5;
        let startPage = Math.max(1, data.page - Math.floor(maxButtons / 2));
        let endPage = Math.min(data.total_pages, startPage + maxButtons - 1);
        
        if (endPage - startPage < maxButtons - 1) {
            startPage = Math.max(1, endPage - maxButtons + 1);
        }

        if (startPage > 1) {
            html += `<button class="pagination-btn" onclick="Jobs.goToPage(1)">1</button>`;
            if (startPage > 2) {
                html += `<span class="pagination-btn" style="border: none;">...</span>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `
                <button class="pagination-btn ${i === data.page ? 'active' : ''}" onclick="Jobs.goToPage(${i})">
                    ${i}
                </button>
            `;
        }

        if (endPage < data.total_pages) {
            if (endPage < data.total_pages - 1) {
                html += `<span class="pagination-btn" style="border: none;">...</span>`;
            }
            html += `<button class="pagination-btn" onclick="Jobs.goToPage(${data.total_pages})">${data.total_pages}</button>`;
        }

        // Next button
        html += `
            <button class="pagination-btn" ${data.page >= data.total_pages ? 'disabled' : ''} onclick="Jobs.goToPage(${data.page + 1})">
                →
            </button>
        `;

        controls.innerHTML = html;
    },

    /**
     * Go to page
     */
    goToPage(page) {
        this.currentPage = page;
        this.loadJobs({ page });
    },

    /**
     * Filter by status
     */
    filterByStatus(status) {
        this.currentStatus = status;
        this.currentPage = 1;
        
        // Update filter tabs
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.status === status);
        });
        
        this.loadJobs({ status, page: 1 });
    },

    /**
     * Search jobs
     */
    search(query) {
        this.currentSearch = query;
        this.currentPage = 1;
        this.loadJobs({ search: query, page: 1 });
    },

    /**
     * View job details - navigate to detail page
     */
    viewJob(jobId) {
        window.location.href = `/job-detail?id=${jobId}`;
    },

    /**
     * Close job modal
     */
    closeModal() {
        document.getElementById('jobModal').classList.remove('active');
    },

    /**
     * Initialize event listeners
     */
    init() {
        // Filter tabs
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.filterByStatus(tab.dataset.status);
            });
        });

        // Search
        let searchTimeout;
        document.getElementById('jobSearch').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                this.search(e.target.value.trim());
            }, 500);
        });

        // Modal close
        document.getElementById('closeJobModal').addEventListener('click', () => this.closeModal());
        document.getElementById('closeJobModalBtn').addEventListener('click', () => this.closeModal());
        document.getElementById('jobModal').addEventListener('click', (e) => {
            if (e.target.id === 'jobModal') this.closeModal();
        });
    }
};

// Make globally available
window.Jobs = Jobs;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Jobs.init();
});
