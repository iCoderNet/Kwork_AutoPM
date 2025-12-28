/**
 * Kwork AI PM - API Client
 */
const API = {
    baseUrl: '/api',
    
    /**
     * Get stored auth token
     */
    getToken() {
        return localStorage.getItem('kwork_pm_token') || sessionStorage.getItem('kwork_pm_token');
    },

    /**
     * Get default headers
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        return headers;
    },

    /**
     * Make API request
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const config = {
            headers: this.getHeaders(),
            ...options,
        };

        try {
            const response = await fetch(url, config);
            
            // Handle 401 Unauthorized
            if (response.status === 401) {
                // Clear tokens and redirect to login
                localStorage.removeItem('kwork_pm_token');
                sessionStorage.removeItem('kwork_pm_token');
                localStorage.removeItem('kwork_pm_user');
                
                if (window.location.pathname !== '/') {
                    window.location.href = '/';
                }
                
                throw new Error('Unauthorized');
            }

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || 'API request failed');
            }
            
            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    /**
     * GET request
     */
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    },

    /**
     * POST request
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    /**
     * PUT request
     */
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data),
        });
    },

    /**
     * DELETE request
     */
    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    // ==================== AUTH ====================
    auth: {
        async login(username, password) {
            return API.post('/auth/login', { username, password });
        },
        
        async logout() {
            return API.post('/auth/logout');
        },
        
        async getMe() {
            return API.get('/auth/me');
        }
    },

    // ==================== JOBS ====================
    jobs: {
        async list(params = {}) {
            return API.get('/jobs', params);
        },
        
        async get(id) {
            return API.get(`/jobs/${id}`);
        },
        
        async updateStatus(id, status) {
            return API.put(`/jobs/${id}/status`, { status });
        },
        
        async getStats() {
            return API.get('/jobs/stats');
        }
    },

    // ==================== SETTINGS ====================
    settings: {
        async getAll() {
            return API.get('/settings');
        },
        
        async update(settings) {
            return API.put('/settings', { settings });
        },
        
        async getAIStatus() {
            return API.get('/settings/ai-status');
        },
        
        async toggleAI() {
            return API.post('/settings/ai-toggle');
        },
        
        async getTelegramStatus() {
            return API.get('/settings/telegram-status');
        },
        
        async testTelegram() {
            return API.post('/settings/test-telegram');
        },
        
        async testAI(jobDescription) {
            return API.post('/settings/test-ai', { job_description: jobDescription });
        }
    },
    
    // Kwork API
    kwork: {
        async login(username, password) {
            return API.post('/kwork/login', { username, password });
        },
        
        async logout() {
            return API.post('/kwork/logout');
        },
        
        async getStatus() {
            return API.get('/kwork/status');
        },
        
        async checkProjects() {
            return API.post('/kwork/check-projects');
        }
    }
};

// Make globally available
window.API = API;
