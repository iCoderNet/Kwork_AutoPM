/**
 * Kwork AI PM - Authentication Module
 */
const Auth = {
    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        const token = localStorage.getItem('kwork_pm_token') || sessionStorage.getItem('kwork_pm_token');
        return !!token;
    },

    /**
     * Get current user data
     */
    getUser() {
        const userData = localStorage.getItem('kwork_pm_user');
        return userData ? JSON.parse(userData) : null;
    },

    /**
     * Login user
     */
    async login(username, password, remember = true) {
        try {
            const response = await API.auth.login(username, password);
            
            // Store token
            const storage = remember ? localStorage : sessionStorage;
            storage.setItem('kwork_pm_token', response.access_token);
            
            // Store user data
            localStorage.setItem('kwork_pm_user', JSON.stringify(response.user));
            
            return { success: true, user: response.user };
        } catch (error) {
            return { 
                success: false, 
                error: error.message || 'Login failed'
            };
        }
    },

    /**
     * Logout user
     */
    async logout() {
        try {
            await API.auth.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear all stored data
            localStorage.removeItem('kwork_pm_token');
            sessionStorage.removeItem('kwork_pm_token');
            localStorage.removeItem('kwork_pm_user');
            
            // Redirect to login
            window.location.href = '/';
        }
    },

    /**
     * Verify current session
     */
    async verifySession() {
        if (!this.isAuthenticated()) {
            return false;
        }

        try {
            const user = await API.auth.getMe();
            localStorage.setItem('kwork_pm_user', JSON.stringify(user));
            return true;
        } catch (error) {
            // Token is invalid
            this.logout();
            return false;
        }
    },

    /**
     * Require authentication (redirect if not logged in)
     */
    async requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/';
            return false;
        }
        
        return await this.verifySession();
    }
};

// Make globally available
window.Auth = Auth;
