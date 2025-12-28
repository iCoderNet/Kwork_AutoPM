/**
 * Kwork AI PM - Dashboard Module
 */
const Dashboard = {
    currentPage: 'dashboard',
    
    /**
     * Initialize dashboard
     */
    async init() {
        // Verify authentication
        const isAuth = await Auth.requireAuth();
        if (!isAuth) return;

        // Load user info
        this.loadUserInfo();
        
        // Setup navigation
        this.setupNavigation();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Load initial data
        await this.loadDashboardData();
        
        console.log('Dashboard initialized');
    },

    /**
     * Load user info into sidebar
     */
    loadUserInfo() {
        const user = Auth.getUser();
        if (user) {
            document.getElementById('userName').textContent = user.username;
            document.getElementById('userAvatar').textContent = user.username.charAt(0).toUpperCase();
        }
    },

    /**
     * Setup navigation
     */
    setupNavigation() {
        const navItems = document.querySelectorAll('.nav-item[data-page]');
        
        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const page = item.dataset.page;
                this.navigateTo(page);
            });
        });

        // Also handle navigation from other elements
        document.querySelectorAll('[data-page]').forEach(el => {
            if (!el.classList.contains('nav-item')) {
                el.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.navigateTo(el.dataset.page);
                });
            }
        });
    },

    /**
     * Navigate to page
     */
    navigateTo(page) {
        // Update nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });

        // Update pages
        document.querySelectorAll('.page').forEach(p => {
            p.classList.add('hidden');
        });
        
        const targetPage = document.getElementById(`page-${page}`);
        if (targetPage) {
            targetPage.classList.remove('hidden');
        }

        // Update page title
        const titles = {
            'dashboard': 'Dashboard',
            'jobs': 'E\'lonlar',
            'ai-settings': 'AI Sozlamalari',
            'telegram-settings': 'Telegram Sozlamalari',
            'kwork-settings': 'Kwork Account'
        };
        document.getElementById('pageTitle').textContent = titles[page] || 'Dashboard';

        // Load page-specific data
        this.currentPage = page;
        this.loadPageData(page);
    },

    /**
     * Load page-specific data
     */
    async loadPageData(page) {
        switch(page) {
            case 'dashboard':
                await this.loadDashboardData();
                break;
            case 'jobs':
                await Jobs.loadJobs();
                break;
            case 'ai-settings':
            case 'telegram-settings':
            case 'kwork-settings':
                await Settings.loadSettings();
                break;
        }
    },

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Logout
        document.getElementById('logoutBtn').addEventListener('click', () => {
            Auth.logout();
        });

        // Refresh
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadPageData(this.currentPage);
            Toast.show('Ma\'lumotlar yangilandi', 'success');
        });

        // AI Toggle
        document.getElementById('aiToggle').addEventListener('change', async (e) => {
            try {
                const result = await API.settings.toggleAI();
                this.updateAIStatus(result.enabled);
                Toast.show(result.message, 'success');
            } catch (error) {
                e.target.checked = !e.target.checked;
                Toast.show('Xatolik yuz berdi', 'error');
            }
        });

        // AI Status button
        document.getElementById('aiStatusBtn').addEventListener('click', () => {
            this.navigateTo('ai-settings');
        });

        // Global search
        document.getElementById('globalSearch').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = e.target.value.trim();
                if (query) {
                    this.navigateTo('jobs');
                    document.getElementById('jobSearch').value = query;
                    Jobs.loadJobs({ search: query });
                }
            }
        });

        // Mobile menu toggle
        document.getElementById('menuToggle').addEventListener('click', () => {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebarOverlay');
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        });

        // Close sidebar when clicking overlay
        document.getElementById('sidebarOverlay').addEventListener('click', () => {
            document.getElementById('sidebar').classList.remove('open');
            document.getElementById('sidebarOverlay').classList.remove('active');
        });

        // Close sidebar when navigating on mobile
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    document.getElementById('sidebar').classList.remove('open');
                    document.getElementById('sidebarOverlay').classList.remove('active');
                }
            });
        });
    },

    /**
     * Load dashboard data
     */
    async loadDashboardData() {
        try {
            // Load stats
            const stats = await API.jobs.getStats();
            this.updateStats(stats);

            // Load AI status
            const aiStatus = await API.settings.getAIStatus();
            this.updateAIStatus(aiStatus.enabled, aiStatus);

            // Load Telegram status
            const telegramStatus = await API.settings.getTelegramStatus();
            this.updateTelegramStatus(telegramStatus);

            // Load recent jobs
            const jobs = await API.jobs.list({ per_page: 5 });
            this.updateRecentJobs(jobs.items);

            // Update pending badge
            if (stats.pending > 0) {
                document.getElementById('pendingBadge').textContent = stats.pending;
                document.getElementById('pendingBadge').style.display = 'block';
            } else {
                document.getElementById('pendingBadge').style.display = 'none';
            }

        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            Toast.show('Ma\'lumotlarni yuklashda xatolik', 'error');
        }
    },

    /**
     * Update stats display
     */
    updateStats(stats) {
        document.getElementById('statTotal').textContent = stats.total || 0;
        document.getElementById('statPending').textContent = stats.pending || 0;
        document.getElementById('statResponded').textContent = stats.responded || 0;
        document.getElementById('statSkipped').textContent = stats.skipped || 0;
    },

    /**
     * Update AI status display
     */
    updateAIStatus(enabled, details = null) {
        const toggle = document.getElementById('aiToggle');
        const statusDot = document.getElementById('aiStatusDot');
        const statusIcon = document.getElementById('aiStatusIcon');

        toggle.checked = enabled;
        
        if (enabled) {
            statusDot.classList.add('active');
            statusDot.classList.remove('inactive');
            statusIcon.textContent = '🟢';
        } else {
            statusDot.classList.remove('active');
            statusDot.classList.add('inactive');
            statusIcon.textContent = '🔴';
        }

        if (details) {
            document.getElementById('aiModel').textContent = details.model || '—';
            document.getElementById('aiApiKey').textContent = details.has_api_key ? '✓ O\'rnatilgan' : '✗ O\'rnatilmagan';
            document.getElementById('aiPrompt').textContent = details.has_prompt ? '✓ O\'rnatilgan' : '✗ O\'rnatilmagan';
        }
    },

    /**
     * Update Telegram status display
     */
    updateTelegramStatus(status) {
        const statusText = status.enabled && status.has_token && status.has_group_id 
            ? '✓ Ulangan' 
            : '✗ Ulanmagan';
        document.getElementById('telegramStatus').textContent = statusText;
    },

    /**
     * Update recent jobs table
     */
    updateRecentJobs(jobs) {
        const tbody = document.getElementById('recentJobsTable');
        
        if (!jobs || jobs.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted" style="padding: 40px;">
                        <div class="empty-state">
                            <div class="empty-state-icon">📭</div>
                            <div class="empty-state-title">E'lonlar yo'q</div>
                            <div class="empty-state-description">Hozircha hech qanday e'lon topilmadi</div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = jobs.map(job => `
            <tr>
                <td class="job-title-cell">
                    <div class="job-title">${this.escapeHtml(job.title)}</div>
                    <div class="job-category">${job.category || 'Kategoriya yo\'q'}</div>
                </td>
                <td>
                    <span class="job-budget">${job.budget || '—'}</span>
                </td>
                <td>
                    ${this.getStatusBadge(job.status)}
                </td>
                <td>
                    ${this.getScoreDisplay(job.confidence_score)}
                </td>
                <td>
                    <span class="job-time">${this.formatTime(job.created_at)}</span>
                </td>
            </tr>
        `).join('');
    },

    /**
     * Get status badge HTML
     */
    getStatusBadge(status) {
        const badges = {
            'pending': '<span class="badge badge-warning">⏳ Kutilmoqda</span>',
            'responded': '<span class="badge badge-success">✅ Javob berildi</span>',
            'skipped': '<span class="badge badge-default">⏭️ O\'tkazildi</span>',
            'failed': '<span class="badge badge-error">❌ Xato</span>'
        };
        return badges[status] || badges['pending'];
    },

    /**
     * Get score display HTML
     */
    getScoreDisplay(score) {
        if (score === null || score === undefined) {
            return '<span class="text-muted">—</span>';
        }
        
        const percentage = Math.round(score * 100);
        let colorClass = 'low';
        if (score >= 0.7) colorClass = 'high';
        else if (score >= 0.4) colorClass = 'medium';

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
     * Format time
     */
    formatTime(dateString) {
        if (!dateString) return '—';
        
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Hozirgina';
        if (minutes < 60) return `${minutes} daqiqa oldin`;
        if (hours < 24) return `${hours} soat oldin`;
        if (days < 7) return `${days} kun oldin`;
        
        return date.toLocaleDateString('uz-UZ');
    },

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

/**
 * Toast notification system
 */
const Toast = {
    show(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toastContainer');
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${icons[type]}</span>
            <div class="toast-content">
                <div class="toast-message">${message}</div>
            </div>
            <button class="toast-close">✕</button>
        `;

        container.appendChild(toast);

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            this.remove(toast);
        });

        // Auto remove
        setTimeout(() => {
            this.remove(toast);
        }, duration);
    },

    remove(toast) {
        toast.style.animation = 'slideInRight 0.3s ease-out reverse';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }
};

// Make globally available
window.Dashboard = Dashboard;
window.Toast = Toast;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Dashboard.init();
});
