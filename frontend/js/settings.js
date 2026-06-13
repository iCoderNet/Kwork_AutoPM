/**
 * Kwork AI PM - Settings Module
 */
const Settings = {
    settings: {},
    loaded: false,

    /**
     * Load all settings
     */
    async loadSettings() {
        if (this.loaded) {
            this.populateFields();
            return;
        }

        try {
            const response = await API.settings.getAll();
            this.settings = response.settings;
            this.loaded = true;
            this.populateFields();
        } catch (error) {
            console.error('Failed to load settings:', error);
            Toast.show('Sozlamalarni yuklashda xatolik', 'error');
        }
    },

    /**
     * Populate form fields with settings
     */
    populateFields() {
        // AI Settings
        if (this.settings.ai) {
            const ai = this.settings.ai;
            this.setFieldValue('aiModelSelect', ai.ai_model?.value);
            this.setFieldValue('aiApiKeyInput', ai.ai_api_key?.has_value ? '••••••••' : '');
            this.setFieldValue('aiBaseUrlInput', ai.ai_base_url?.value || '');
            this.setFieldValue('aiPromptInput', ai.ai_prompt?.value);
        }

        // Telegram Settings
        if (this.settings.telegram) {
            const telegram = this.settings.telegram;
            document.getElementById('telegramEnabled').checked = telegram.telegram_enabled?.value === 'true';
            this.setFieldValue('telegramBotToken', telegram.telegram_bot_token?.has_value ? '••••••••' : '');
            this.setFieldValue('telegramGroupId', telegram.telegram_group_id?.value);
        }

        // Kwork Settings
        if (this.settings.kwork) {
            const kwork = this.settings.kwork;
            this.setFieldValue('kworkUsername', kwork.kwork_username?.value);
            this.setFieldValue('kworkPassword', kwork.kwork_password?.has_value ? '••••••••' : '');
        }

        // System Settings
        if (this.settings.system) {
            const system = this.settings.system;
            this.setFieldValue('scanInterval', system.scan_interval?.value || '60');
            document.getElementById('autoRespond').checked = system.auto_respond?.value === 'true';
        }
    },

    /**
     * Set field value helper
     */
    setFieldValue(id, value) {
        const field = document.getElementById(id);
        if (field && value !== undefined && value !== null) {
            field.value = value;
        }
    },

    /**
     * Save AI settings
     */
    async saveAISettings() {
        const model = document.getElementById('aiModelSelect').value;
        const settings = {
            ai_model: model,
            ai_prompt: document.getElementById('aiPromptInput').value
        };

        // API key — faqat o'zgargan bo'lsa
        const apiKey = document.getElementById('aiApiKeyInput').value;
        if (apiKey && apiKey !== '••••••••') {
            settings.ai_api_key = apiKey;
        }

        // Base URL — kiritilgan bo'lsa ishlatamiz, aks holda model bo'yicha default
        const baseUrlInput = document.getElementById('aiBaseUrlInput');
        const baseUrlVal = baseUrlInput ? baseUrlInput.value.trim() : '';
        if (baseUrlVal) {
            settings.ai_base_url = baseUrlVal;
        } else if (model === 'openai/gpt-oss-120b') {
            settings.ai_base_url = 'https://p950-w009-runai-p950.runai-inference.dc.uz/v1';
        } else {
            settings.ai_base_url = '';
        }

        await this.saveSettings(settings, 'AI sozlamalari saqlandi');
    },

    /**
     * Save Telegram settings
     */
    async saveTelegramSettings() {
        const settings = {
            telegram_enabled: document.getElementById('telegramEnabled').checked ? 'true' : 'false',
            telegram_group_id: document.getElementById('telegramGroupId').value
        };

        // Only include bot token if changed
        const botToken = document.getElementById('telegramBotToken').value;
        if (botToken && botToken !== '••••••••') {
            settings.telegram_bot_token = botToken;
        }

        await this.saveSettings(settings, 'Telegram sozlamalari saqlandi');
    },

    /**
     * Save Kwork settings
     */
    async saveKworkSettings() {
        const settings = {
            kwork_username: document.getElementById('kworkUsername').value,
            scan_interval: document.getElementById('scanInterval').value,
            auto_respond: document.getElementById('autoRespond').checked ? 'true' : 'false'
        };

        // Only include password if changed
        const password = document.getElementById('kworkPassword').value;
        if (password && password !== '••••••••') {
            settings.kwork_password = password;
        }

        await this.saveSettings(settings, 'Kwork sozlamalari saqlandi');
    },

    /**
     * Save settings to API
     */
    async saveSettings(settings, successMessage) {
        try {
            await API.settings.update(settings);
            this.loaded = false; // Force reload on next load
            Toast.show(successMessage, 'success');
        } catch (error) {
            console.error('Failed to save settings:', error);
            Toast.show('Sozlamalarni saqlashda xatolik', 'error');
        }
    },

    /**
     * Test Telegram connection
     */
    async testTelegram() {
        const btn = document.getElementById('testTelegram');
        const originalText = btn.innerHTML;
        
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width: 16px; height: 16px;"></span> Test...';

        try {
            const result = await API.settings.testTelegram();
            
            if (result.success) {
                Toast.show(result.message, 'success');
                if (result.bot_info) {
                    Toast.show(`Bot: @${result.bot_info.username}`, 'info');
                }
            } else {
                Toast.show(result.message, 'error');
            }
        } catch (error) {
            console.error('Telegram test failed:', error);
            Toast.show('Telegram testida xatolik', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    },

    /**
     * Reset settings to loaded values
     */
    resetSettings(category) {
        this.populateFields();
        Toast.show('O\'zgarishlar bekor qilindi', 'info');
    },

    /**
     * Test AI with job description
     */
    async testAI() {
        const input = document.getElementById('aiTestInput');
        const btn = document.getElementById('testAIBtn');
        const resultContainer = document.getElementById('aiTestResultContainer');
        const resultDiv = document.getElementById('aiTestResult');
        
        const jobDescription = input.value.trim();
        
        if (!jobDescription) {
            Toast.show('E\'lon matnini kiriting', 'warning');
            return;
        }
        
        // Show loading state
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="width: 16px; height: 16px;"></span> AI javob bermoqda...';
        resultContainer.style.display = 'block';
        resultDiv.className = 'ai-test-result loading';
        resultDiv.innerHTML = '<span class="spinner"></span>';
        
        try {
            const result = await API.settings.testAI(jobDescription);
            
            if (result.success) {
                resultDiv.className = 'ai-test-result';
                resultDiv.innerHTML = this.formatAIResponse(result.text, result.model);
                Toast.show(`AI javob berdi (${result.model})`, 'success');
            } else {
                resultDiv.className = 'ai-test-result error';
                resultDiv.textContent = result.error || 'Noma\'lum xato';
                Toast.show('AI xatolik qaytardi', 'error');
            }
        } catch (error) {
            console.error('AI test failed:', error);
            resultDiv.className = 'ai-test-result error';
            resultDiv.textContent = `Xatolik: ${error.message}`;
            Toast.show('AI testida xatolik', 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🚀 AI bilan test qilish';
        }
    },
    
    /**
     * Format AI response with styling
     */
    formatAIResponse(text, model) {
        // Add model badge at the top
        let html = `<div class="ai-response-header">
            <span class="badge badge-primary">${model}</span>
        </div>`;
        
        // Remove markdown code block markers
        let cleanText = text
            .replace(/```json\s*/gi, '')
            .replace(/```\s*/gi, '')
            .trim();
        
        // Try to parse as JSON
        try {
            const jsonData = JSON.parse(cleanText);
            html += this.formatJSONResponse(jsonData);
        } catch (e) {
            // Not valid JSON, just format as text
            html += `<div class="ai-response-text">${this.escapeHtml(cleanText).replace(/\n/g, '<br>')}</div>`;
        }
        
        return html;
    },
    
    /**
     * Format JSON response nicely
     */
    formatJSONResponse(data) {
        let html = '<div class="ai-json-response">';
        
        // Should respond (can_take)
        if (data.should_respond !== undefined || data.can_take !== undefined) {
            const shouldRespond = data.should_respond ?? data.can_take;
            html += `<div class="ai-field ${shouldRespond ? 'positive' : 'negative'}">
                <span class="ai-field-label">Qabul qilish:</span>
                <span class="ai-field-value">${shouldRespond ? '✅ Ha, olish mumkin' : '❌ Yo\'q, o\'tkazib yuborish'}</span>
            </div>`;
        }
        
        // Confidence score
        if (data.confidence_score !== undefined) {
            let score = data.confidence_score;
            if (score <= 1) score = Math.round(score * 100);
            const cls = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';
            html += `<div class="ai-field">
                <span class="ai-field-label">Ishonch darajasi:</span>
                <span class="ai-field-value score ${cls}">${score}%</span>
                <div class="ai-score-bar"><div class="ai-score-fill ${cls}" style="width: ${score}%"></div></div>
            </div>`;
        }
        
        // Risk score
        if (data.risk_score !== undefined) {
            let score = data.risk_score;
            if (score <= 1) score = Math.round(score * 100);
            const cls = score <= 30 ? 'high' : score <= 65 ? 'medium' : 'low';
            html += `<div class="ai-field">
                <span class="ai-field-label">Xavf darajasi:</span>
                <span class="ai-field-value score ${cls}">${score}%</span>
                <div class="ai-score-bar"><div class="ai-score-fill ${cls}" style="width: ${score}%"></div></div>
            </div>`;
        }
        
        // Reason (supports both string and {ru, uz} object)
        if (data.reason) {
            const reasonText = typeof data.reason === 'object' 
                ? (data.reason.uz || data.reason.ru) 
                : data.reason;
            html += `<div class="ai-field reason">
                <span class="ai-field-label">Sabab:</span>
                <span class="ai-field-value">${this.escapeHtml(reasonText)}</span>
            </div>`;
        }
        
        // Estimated price
        if (data.estimated_price_rub) {
            html += `<div class="ai-field">
                <span class="ai-field-label">Taxminiy narx:</span>
                <span class="ai-field-value price">${data.estimated_price_rub} ₽</span>
            </div>`;
        }
        
        // Estimated time (supports estimated_time_human)
        const timeValue = data.estimated_time_human || data.estimated_time;
        if (timeValue) {
            html += `<div class="ai-field">
                <span class="ai-field-label">Taxminiy muddat:</span>
                <span class="ai-field-value">${timeValue}</span>
            </div>`;
        }
        
        // Proposal text (supports both string and {ru, uz} object)
        const proposalData = data.proposal_text || data.response_text;
        if (proposalData) {
            const proposalRu = typeof proposalData === 'object' ? proposalData.ru : proposalData;
            const proposalUz = typeof proposalData === 'object' ? proposalData.uz : null;
            
            if (proposalRu || proposalUz) {
                html += `<div class="ai-field proposal">
                    <span class="ai-field-label">Otklik matni:</span>`;
                
                if (proposalRu) {
                    html += `<div class="ai-proposal-text">
                        <div class="proposal-lang">🇷🇺 Ruscha:</div>
                        ${this.escapeHtml(proposalRu)}
                    </div>`;
                }
                
                if (proposalUz) {
                    html += `<div class="ai-proposal-text" style="margin-top: 12px;">
                        <div class="proposal-lang">🇺🇿 O'zbekcha:</div>
                        ${this.escapeHtml(proposalUz)}
                    </div>`;
                }
                
                html += `</div>`;
            }
        }
        
        // Full task text (cleaned from HTML) - supports {ru, uz}
        if (data.full_task_text) {
            const taskRu = typeof data.full_task_text === 'object' ? data.full_task_text.ru : data.full_task_text;
            const taskUz = typeof data.full_task_text === 'object' ? data.full_task_text.uz : null;
            
            if (taskRu || taskUz) {
                html += `<div class="ai-field task-text">
                    <span class="ai-field-label">Tozalangan e'lon matni:</span>`;
                
                if (taskRu) {
                    html += `<div class="ai-task-text">
                        <div class="proposal-lang">🇷🇺 Ruscha:</div>
                        ${this.escapeHtml(taskRu)}
                    </div>`;
                }
                
                if (taskUz) {
                    html += `<div class="ai-task-text" style="margin-top: 12px;">
                        <div class="proposal-lang">🇺🇿 O'zbekcha:</div>
                        ${this.escapeHtml(taskUz)}
                    </div>`;
                }
                
                html += `</div>`;
            }
        }
        
        html += '</div>';
        return html;
    },
    
    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Initialize event listeners
     */
    init() {
        // AI Settings
        document.getElementById('saveAISettings').addEventListener('click', () => this.saveAISettings());
        document.getElementById('resetAISettings').addEventListener('click', () => this.resetSettings('ai'));
        document.getElementById('testAIBtn').addEventListener('click', () => this.testAI());

        // Telegram Settings
        document.getElementById('saveTelegramSettings').addEventListener('click', () => this.saveTelegramSettings());
        document.getElementById('resetTelegramSettings').addEventListener('click', () => this.resetSettings('telegram'));
        document.getElementById('testTelegram').addEventListener('click', () => this.testTelegram());

        // Kwork Settings
        document.getElementById('saveKworkSettings').addEventListener('click', () => this.saveKworkSettings());
        document.getElementById('resetKworkSettings').addEventListener('click', () => this.resetSettings('kwork'));
        
        // Kwork Login/Logout
        this.initKwork();
        
        // Fullscreen Prompt Editor
        this.initPromptEditor();
    },
    
    /**
     * Initialize Kwork login/logout handlers
     */
    initKwork() {
        const loginBtn = document.getElementById('kworkLoginBtn');
        const logoutBtn = document.getElementById('kworkLogoutBtn');
        const checkBtn = document.getElementById('checkProjectsBtn');
        const statusPanel = document.getElementById('kworkStatusPanel');
        const statusDot = document.getElementById('kworkStatusDot');
        const statusText = document.getElementById('kworkStatusText');
        const usernameDisplay = document.getElementById('kworkUsernameDisplay');
        const loginCard = document.getElementById('kworkLoginCard');
        
        // Load initial status
        this.loadKworkStatus();
        
        // Login handler
        loginBtn?.addEventListener('click', async () => {
            const username = document.getElementById('kworkUsername').value;
            const password = document.getElementById('kworkPassword').value;
            
            if (!username || !password) {
                Toast.show('Login va parolni kiriting', 'warning');
                return;
            }
            
            const originalText = loginBtn.innerHTML;
            loginBtn.disabled = true;
            loginBtn.innerHTML = '<span class="spinner" style="width: 16px; height: 16px;"></span> Kirilmoqda...';
            
            try {
                const result = await API.kwork.login(username, password);
                
                if (result.success) {
                    Toast.show('Muvaffaqiyatli kirdingiz!', 'success');
                    this.loadKworkStatus();
                    document.getElementById('kworkPassword').value = '';
                } else {
                    Toast.show(result.error || 'Login xatosi', 'error');
                }
            } catch (error) {
                Toast.show('Login xatosi: ' + error.message, 'error');
            } finally {
                loginBtn.disabled = false;
                loginBtn.innerHTML = originalText;
            }
        });
        
        // Logout handler
        logoutBtn?.addEventListener('click', async () => {
            if (!confirm('Chiqishni tasdiqlaysizmi?')) return;
            
            try {
                await API.kwork.logout();
                Toast.show('Chiqdingiz', 'success');
                this.loadKworkStatus();
            } catch (error) {
                Toast.show('Chiqishda xato', 'error');
            }
        });
        
        // Check projects handler
        checkBtn?.addEventListener('click', async () => {
            const originalText = checkBtn.innerHTML;
            checkBtn.disabled = true;
            checkBtn.innerHTML = '<span class="spinner" style="width: 16px; height: 16px;"></span> Tekshirilmoqda...';
            
            try {
                const result = await API.kwork.checkProjects();
                
                if (result.success) {
                    Toast.show(result.message, 'success');
                } else {
                    Toast.show(result.error || 'Xatolik', 'error');
                }
            } catch (error) {
                Toast.show('Xatolik: ' + error.message, 'error');
            } finally {
                checkBtn.disabled = false;
                checkBtn.innerHTML = originalText;
            }
        });
    },
    
    /**
     * Load Kwork status
     */
    async loadKworkStatus() {
        const statusPanel = document.getElementById('kworkStatusPanel');
        const statusDot = document.getElementById('kworkStatusDot');
        const statusText = document.getElementById('kworkStatusText');
        const usernameDisplay = document.getElementById('kworkUsernameDisplay');
        const loginCard = document.getElementById('kworkLoginCard');
        const logoutBtn = document.getElementById('kworkLogoutBtn');
        const checkBtn = document.getElementById('checkProjectsBtn');
        
        try {
            const status = await API.kwork.getStatus();
            
            if (status.logged_in) {
                statusPanel?.classList.remove('offline');
                statusDot?.classList.add('online');
                statusDot?.classList.remove('offline');
                if (statusText) statusText.textContent = 'Ulangan ✓';
                if (usernameDisplay) usernameDisplay.textContent = status.username || status.user_id || '-';
                loginCard?.classList.add('hidden');
                logoutBtn?.classList.remove('hidden');
                if (checkBtn) checkBtn.disabled = false;
            } else {
                statusPanel?.classList.add('offline');
                statusDot?.classList.remove('online');
                statusDot?.classList.add('offline');
                if (statusText) statusText.textContent = 'Ulanmagan';
                if (usernameDisplay) usernameDisplay.textContent = '-';
                loginCard?.classList.remove('hidden');
                logoutBtn?.classList.add('hidden');
                if (checkBtn) checkBtn.disabled = true;
            }
        } catch (error) {
            console.error('Kwork status xatosi:', error);
        }
    },
    
    /**
     * Initialize fullscreen prompt editor
     */
    initPromptEditor() {
        const modal = document.getElementById('promptEditorModal');
        const openBtn = document.getElementById('promptFullscreenBtn');
        const closeBtn = document.getElementById('closePromptEditor');
        const cancelBtn = document.getElementById('cancelPromptEdit');
        const applyBtn = document.getElementById('applyPromptEdit');
        const promptInput = document.getElementById('aiPromptInput');
        const fullscreenInput = document.getElementById('fullscreenPromptInput');
        const charCount = document.getElementById('promptCharCount');
        
        // Open fullscreen editor
        openBtn.addEventListener('click', () => {
            fullscreenInput.value = promptInput.value;
            charCount.textContent = fullscreenInput.value.length;
            modal.classList.add('active');
            fullscreenInput.focus();
        });
        
        // Close handlers
        const closeModal = () => {
            modal.classList.remove('active');
        };
        
        closeBtn.addEventListener('click', closeModal);
        cancelBtn.addEventListener('click', closeModal);
        
        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });
        
        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('active')) {
                closeModal();
            }
        });
        
        // Apply changes
        applyBtn.addEventListener('click', () => {
            promptInput.value = fullscreenInput.value;
            closeModal();
            Toast.show('Prompt qo\'llandi', 'success');
        });
        
        // Character count update
        fullscreenInput.addEventListener('input', () => {
            charCount.textContent = fullscreenInput.value.length;
        });
        
        // Ctrl+Enter to apply
        fullscreenInput.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                promptInput.value = fullscreenInput.value;
                closeModal();
                Toast.show('Prompt qo\'llandi (Ctrl+Enter)', 'success');
            }
        });
    }
};

// Make globally available
window.Settings = Settings;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Settings.init();
});
