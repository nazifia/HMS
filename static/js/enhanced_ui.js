// Enhanced UI JavaScript for HMS

// Global configuration
const HMSUI = {
    config: {
        animationDuration: 300,
        notificationTimeout: 5000,
        autoRefreshInterval: 0, // Disabled for manual operation
        sessionWarningTime: 600000, // 10 minutes
        sessionLogoutTime: 1200000 // 20 minutes
    },
    
    // Session management
    session: {
        lastActivity: new Date().getTime(),
        timeout: null,
        warningShown: false,
        
        init() {
            this.updateActivity();
            this.startTimer();
            this.addEventListener();
        },
        
        updateActivity() {
            this.lastActivity = new Date().getTime();
            this.warningShown = false;
        },
        
        startTimer() {
            if (this.timeout) {
                clearTimeout(this.timeout);
            }
            
            const self = this;
            this.timeout = setTimeout(() => {
                self.checkSession();
            }, 60000); // Check every minute
        },
        
        checkSession() {
            const now = new Date().getTime();
            const inactiveTime = now - this.lastActivity;
            
            if (inactiveTime > this.config.sessionLogoutTime) {
                // Auto logout
                window.location.href = '/logout/';
            } else if (inactiveTime > this.config.sessionWarningTime && !this.warningShown) {
                // Show warning
                this.showSessionWarning();
                this.warningShown = true;
            }
            
            this.startTimer();
        },
        
        showSessionWarning() {
            const warningModal = this.createModal({
                title: 'Session Warning',
                content: 'Your session will expire in 10 minutes. Do you want to continue?',
                buttons: [
                    { text: 'Continue', class: 'btn-primary', action: () => this.updateActivity() },
                    { text: 'Logout', class: 'btn-secondary', action: () => window.location.href = '/logout/' }
                ]
            });
            
            // Auto logout after 10 minutes
            setTimeout(() => {
                if (this.warningShown) {
                    window.location.href = '/logout/';
                }
            }, 600000);
        },
        
        addEventListener() {
            ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
                document.addEventListener(event, () => this.updateActivity());
            });
        }
    },
    
    // Notification system
    notifications: {
        container: null,
        
        init() {
            this.container = this.createContainer();
            this.setupWebSocket();
        },
        
        createContainer() {
            const container = document.createElement('div');
            container.className = 'notification-container';
            container.style.cssText = `
                position: fixed;
                top: 60px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
            return container;
        },
        
        show(message, type = 'info', options = {}) {
            const notification = this.createNotification(message, type, options);
            this.container.appendChild(notification);
            
            // Animate in
            requestAnimationFrame(() => {
                notification.classList.add('show');
            });
            
            // Auto dismiss
            if (!options.sticky) {
                setTimeout(() => this.dismiss(notification), options.duration || this.config.notificationTimeout);
            }
            
            return notification;
        },
        
        createNotification(message, type, options) {
            const notification = document.createElement('div');
            const id = 'notification-' + Date.now();
            
            notification.id = id;
            notification.className = `notification notification-${type}`;
            notification.style.cssText = `
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                margin-bottom: 10px;
                padding: 16px;
                transform: translateX(100%);
                transition: transform ${this.config.animationDuration}ms ease;
                position: relative;
                border-left: 4px solid ${this.getTypeColor(type)};
            `;
            
            const icon = this.getIcon(type);
            const title = options.title || this.getTypeTitle(type);
            
            notification.innerHTML = `
                <div class="d-flex align-items-start">
                    <div class="me-3">
                        <i class="${icon} fa-lg" style="color: ${this.getTypeColor(type)}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-semibold">${title}</div>
                        <div class="text-secondary small">${message}</div>
                        ${options.action ? `<button class="btn btn-sm btn-primary mt-2" onclick="${options.action}">${options.actionText || 'View'}</button>` : ''}
                    </div>
                    <button class="btn-close btn-sm" onclick="HMSUI.notifications.dismiss('${id}')"></button>
                </div>
            `;
            
            return notification;
        },
        
        dismiss(notification) {
            if (typeof notification === 'string') {
                notification = document.getElementById(notification);
            }
            
            if (notification) {
                notification.classList.remove('show');
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.parentNode.removeChild(notification);
                    }
                }, this.config.animationDuration);
            }
        },
        
        getTypeColor(type) {
            const colors = {
                info: '#17a2b8',
                success: '#28a745',
                warning: '#ffc107',
                error: '#dc3545'
            };
            return colors[type] || colors.info;
        },
        
        getIcon(type) {
            const icons = {
                info: 'fas fa-info-circle',
                success: 'fas fa-check-circle',
                warning: 'fas fa-exclamation-triangle',
                error: 'fas fa-exclamation-circle'
            };
            return icons[type] || icons.info;
        },
        
        getTypeTitle(type) {
            const titles = {
                info: 'Information',
                success: 'Success',
                warning: 'Warning',
                error: 'Error'
            };
            return titles[type] || titles.info;
        },
        
        setupWebSocket() {
            // WebSocket connection for real-time notifications
            if (window.wsUrl) {
                const ws = new WebSocket(window.wsUrl);
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.show(data.message, data.type, data.options);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
                
                ws.onclose = () => {
                    // Reconnect after 5 seconds
                    setTimeout(() => this.setupWebSocket(), 5000);
                };
            }
        }
    },
    
    // Modal system
    modals: {
        current: null,
        
        show(options) {
            if (this.current) {
                this.current.close();
            }
            
            const modal = new EnhancedModal(options);
            this.current = modal;
            
            return modal;
        },
        
        close() {
            if (this.current) {
                this.current.close();
                this.current = null;
            }
        },
        
        confirm(message, callback, options = {}) {
            return this.show({
                title: options.title || 'Confirm',
                content: message,
                buttons: [
                    { text: 'Cancel', class: 'btn-secondary' },
                    { text: 'Confirm', class: 'btn-primary', action: callback }
                ],
                ...options
            });
        },
        
        alert(message, type = 'info', options = {}) {
            return this.show({
                title: options.title || this.getTitle(type),
                content: message,
                buttons: [
                    { text: 'OK', class: 'btn-primary' }
                ],
                ...options
            });
        },
        
        getTitle(type) {
            const titles = {
                info: 'Information',
                success: 'Success',
                warning: 'Warning',
                error: 'Error'
            };
            return titles[type] || titles.info;
        }
    },
    
    // Loading states
    loading: {
        states: new Map(),
        
        show(element, options = {}) {
            const id = this.getId(element);
            const loadingState = this.createLoadingState(options);
            
            element.style.position = 'relative';
            element.appendChild(loadingState);
            this.states.set(id, loadingState);
            
            // Disable element
            if (options.disable) {
                element.disabled = true;
            }
        },
        
        hide(element) {
            const id = this.getId(element);
            const loadingState = this.states.get(id);
            
            if (loadingState) {
                loadingState.remove();
                this.states.delete(id);
            }
            
            // Re-enable element
            element.disabled = false;
        },
        
        createLoadingState(options) {
            const container = document.createElement('div');
            container.className = 'loading-overlay';
            container.style.cssText = `
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(255,255,255,0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                backdrop-filter: blur(2px);
                border-radius: 8px;
            `;
            
            const spinner = document.createElement('div');
            spinner.className = 'loading-spinner';
            spinner.style.cssText = `
                width: 40px;
                height: 40px;
                border: 4px solid rgba(102, 126, 234, 0.2);
                border-top: 4px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            `;
            
            if (options.message) {
                const message = document.createElement('div');
                message.className = 'loading-message';
                message.textContent = options.message;
                message.style.cssText = `
                    margin-top: 10px;
                    color: #667eea;
                    font-weight: 600;
                `;
                container.appendChild(message);
            }
            
            container.appendChild(spinner);
            return container;
        },
        
        getId(element) {
            return element.dataset.loadingId || (element.dataset.loadingId = 'loading-' + Math.random().toString(36).substr(2, 9));
        }
    },
    
    // Form enhancements
    forms: {
        init() {
            this.addGlobalEventListeners();
            this.initValidation();
            this.initFileUploads();
        },
        
        addGlobalEventListeners() {
            // Auto-save functionality
            document.querySelectorAll('.form-auto-save').forEach(form => {
                let timeout;
                form.addEventListener('input', () => {
                    clearTimeout(timeout);
                    timeout = setTimeout(() => this.autoSave(form), 1000);
                });
            });
            
            // Form validation
            document.addEventListener('submit', (e) => {
                const form = e.target;
                if (form.classList.contains('form-validate')) {
                    if (!this.validate(form)) {
                        e.preventDefault();
                    }
                }
            });
            
            // Character counting
            document.querySelectorAll('[data-maxlength]').forEach(field => {
                this.addCharacterCount(field);
            });
        },
        
        validate(form) {
            let isValid = true;
            const fields = form.querySelectorAll('[data-validate]');
            
            fields.forEach(field => {
                const rules = field.dataset.validate.split('|');
                const error = this.validateField(field, rules);
                
                if (error) {
                    this.showFieldError(field, error);
                    isValid = false;
                } else {
                    this.clearFieldError(field);
                }
            });
            
            return isValid;
        },
        
        validateField(field, rules) {
            const value = field.value.trim();
            const name = field.name || field.id || 'Field';
            
            for (const rule of rules) {
                if (rule === 'required' && !value) {
                    return `${name} is required`;
                }
                
                if (rule === 'email' && value && !this.isValidEmail(value)) {
                    return `Please enter a valid email address`;
                }
                
                if (rule.startsWith('min:') && value) {
                    const length = parseInt(rule.split(':')[1]);
                    if (value.length < length) {
                        return `${name} must be at least ${length} characters`;
                    }
                }
                
                if (rule.startsWith('max:') && value) {
                    const length = parseInt(rule.split(':')[1]);
                    if (value.length > length) {
                        return `${name} must not exceed ${length} characters`;
                    }
                }
                
                if (rule.startsWith('pattern:') && value) {
                    const pattern = new RegExp(rule.split(':')[1].replace(/_/g, '|'));
                    if (!pattern.test(value)) {
                        return `${name} format is invalid`;
                    }
                }
            }
            
            return null;
        },
        
        isValidEmail(email) {
            const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return pattern.test(email);
        },
        
        showFieldError(field, error) {
            const feedback = field.nextElementSibling;
            if (feedback && feedback.classList.contains('field-feedback')) {
                feedback.textContent = error;
                feedback.style.display = 'block';
            } else {
                const newFeedback = document.createElement('div');
                newFeedback.className = 'field-feedback text-danger small mt-1';
                newFeedback.textContent = error;
                newFeedback.style.display = 'block';
                field.parentNode.insertBefore(newFeedback, field.nextSibling);
            }
            
            field.classList.add('is-invalid');
        },
        
        clearFieldError(field) {
            field.classList.remove('is-invalid');
            const feedback = field.nextElementSibling;
            if (feedback && feedback.classList.contains('field-feedback')) {
                feedback.style.display = 'none';
            }
        },
        
        addCharacterCount(field) {
            const maxLength = parseInt(field.dataset.maxlength);
            const counter = document.createElement('div');
            counter.className = 'character-counter text-muted small mt-1';
            
            function updateCount() {
                const remaining = maxLength - field.value.length;
                counter.textContent = `${remaining} characters remaining`;
                counter.className = remaining < 10 ? 'character-counter text-danger small mt-1' : 'character-counter text-muted small mt-1';
            }
            
            field.parentNode.insertBefore(counter, field.nextSibling);
            field.addEventListener('input', updateCount);
            updateCount();
        },
        
        autoSave(form) {
            const formData = new FormData(form);
            const url = form.dataset.autoSave;
            
            if (!url) return;
            
            fetch(url, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                HMSUI.notifications.show('Changes saved automatically', 'success');
            })
            .catch(error => {
                console.error('Auto-save failed:', error);
            });
        },
        
        // File upload enhancements
        initFileUploads() {
            document.querySelectorAll('input[type="file"]').forEach(input => {
                this.enhanceFileInput(input);
            });
        },
        
        enhanceFileInput(input) {
            const wrapper = document.createElement('div');
            wrapper.className = 'file-input-wrapper';
            
            const preview = document.createElement('div');
            preview.className = 'file-preview';
            preview.style.cssText = `
                margin-top: 10px;
                min-height: 100px;
                border: 2px dashed #ddd;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: #6c757d;
            `;
            
            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);
            wrapper.appendChild(preview);
            
            input.addEventListener('change', (e) => {
                this.handleFileSelect(e.target, preview);
            });
        },
        
        handleFileSelect(input, preview) {
            const files = Array.from(input.files);
            preview.innerHTML = '';
            
            files.forEach(file => {
                const fileDiv = document.createElement('div');
                fileDiv.className = 'file-item mb-2';
                fileDiv.style.cssText = 'display: flex; align-items: center; padding: 5px; background: #f8f9fa; border-radius: 4px;';
                
                if (file.type.startsWith('image/')) {
                    const img = document.createElement('img');
                    img.style.cssText = 'width: 40px; height: 40px; object-fit: cover; border-radius: 4px; margin-right: 10px;';
                    img.url = URL.createObjectURL(file);
                    img.onload = () => URL.revokeObjectURL(img.url);
                    fileDiv.appendChild(img);
                }
                
                const info = document.createElement('div');
                info.innerHTML = `
                    <div class="fw-semibold">${file.name}</div>
                    <div class="text-muted small">${this.formatFileSize(file.size)}</div>
                `;
                
                fileDiv.appendChild(info);
                preview.appendChild(fileDiv);
            });
        },
        
        formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    },
    
    // Initialization
    init() {
        this.session.init();
        this.notifications.init();
        this.forms.init();
        
        // Initialize tooltips and popovers
        document.addEventListener('DOMContentLoaded', () => {
            const tooltips = document.querySelectorAll('[title]');
            tooltips.forEach(el => new bootstrap.Tooltip(el));
            
            const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
            popovers.forEach(el => new bootstrap.Popover(el));
        });
    }
};

// Enhanced Modal class
class EnhancedModal {
    constructor(options) {
        this.options = {
            size: 'md',
            backdrop: true,
            keyboard: true,
            show: true,
            ...options
        };
        
        this.element = this.create();
        this.bindEvents();
        
        if (this.options.show) {
            this.show();
        }
    }
    
    create() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.setAttribute('tabindex', '-1');
        modal.innerHTML = `
            <div class="modal-dialog modal-${this.options.size}">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${this.options.title || 'Modal'}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        ${this.options.content || ''}
                    </div>
                    ${this.createFooter()}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        return modal;
    }
    
    createFooter() {
        if (!this.options.buttons) return '';
        
        const buttons = this.options.buttons.map(btn => `
            <button type="button" class="btn ${btn.class || 'btn-secondary'}" 
                    onclick="${btn.action ? `(${btn.action})()` : ''}"
                    data-bs-dismiss="${btn.dismiss ? 'modal' : ''}">
                ${btn.text}
            </button>
        `).join('');
        
        return `
            <div class="modal-footer">
                ${buttons}
            </div>
        `;
    }
    
    bindEvents() {
        this.element.addEventListener('hidden.bs.modal', () => {
            this.destroy();
        });
        
        if (this.options.onShow) {
            this.element.addEventListener('show.bs.modal', this.options.onShow);
        }
        
        if (this.options.onHide) {
            this.element.addEventListener('hide.bs.modal', this.options.onHide);
        }
    }
    
    show() {
        this.modal = new bootstrap.Modal(this.element, {
            backdrop: this.options.backdrop,
            keyboard: this.options.keyboard
        });
        this.modal.show();
    }
    
    hide() {
        if (this.modal) {
            this.modal.hide();
        }
    }
    
    close() {
        this.hide();
    }
    
    destroy() {
        if (this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
    }
}

// Polyfills for older browsers
if (!window.fetch) {
    // Simple fetch polyfill
    window.fetch = function(url, options) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open(options.method || 'GET', url);
            
            if (options.headers) {
                Object.keys(options.headers).forEach(key => {
                    xhr.setRequestHeader(key, options.headers[key]);
                });
            }
            
            xhr.onload = () => resolve({
                ok: xhr.status >= 200 && xhr.status < 300,
                status: xhr.status,
                headers: xhr.getAllResponseHeaders(),
                json: () => Promise.resolve(JSON.parse(xhr.responseText)),
                text: () => Promise.resolve(xhr.responseText)
            });
            
            xhr.onerror = () => reject(new Error('Network error'));
            xhr.send(options.body);
        });
    };
}

// Initialize HMS UI
window.HMSUI = HMSUI;
HMSUI.init();

// Export for global access
window.showNotification = (message, type, options) => HMSUI.notifications.show(message, type, options);
window.showModal = (options) => HMSUI.modals.show(options);
window.showConfirm = (message, callback, options) => HMSUI.modals.confirm(message, callback, options);
