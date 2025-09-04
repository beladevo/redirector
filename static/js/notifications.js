/**
 * Redirector Dashboard - Toast Notification System
 * Modern, accessible toast notifications with animations
 */

(function(window) {
    'use strict';

    // Create namespace
    window.Notifications = window.Notifications || {};

    const NOTIFICATION_TYPES = {
        SUCCESS: 'success',
        ERROR: 'error',
        WARNING: 'warning',
        INFO: 'info'
    };

    const POSITIONS = {
        TOP_RIGHT: 'top-right',
        TOP_LEFT: 'top-left',
        TOP_CENTER: 'top-center',
        BOTTOM_RIGHT: 'bottom-right',
        BOTTOM_LEFT: 'bottom-left',
        BOTTOM_CENTER: 'bottom-center'
    };

    let container = null;
    let notifications = new Map();
    let notificationCounter = 0;

    // Default configuration
    const defaultConfig = {
        position: POSITIONS.TOP_RIGHT,
        duration: 5000,
        maxNotifications: 5,
        pauseOnHover: true,
        closeButton: true,
        progressBar: true,
        sound: false,
        animations: true
    };

    /**
     * Create notification container if it doesn't exist
     */
    function ensureContainer() {
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            container.setAttribute('aria-live', 'polite');
            container.setAttribute('aria-label', 'Notifications');
            document.body.appendChild(container);
        }
    }

    /**
     * Create a notification element
     * @param {Object} options - Notification options
     * @returns {HTMLElement} Notification element
     */
    function createNotificationElement(options) {
        const {
            type = NOTIFICATION_TYPES.INFO,
            title,
            message,
            closeButton = defaultConfig.closeButton,
            progressBar = defaultConfig.progressBar,
            icon,
            actions = []
        } = options;

        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.setAttribute('role', 'alert');
        notification.setAttribute('aria-atomic', 'true');

        // Icons for different types
        const icons = {
            [NOTIFICATION_TYPES.SUCCESS]: icon || '✅',
            [NOTIFICATION_TYPES.ERROR]: icon || '❌',
            [NOTIFICATION_TYPES.WARNING]: icon || '⚠️',
            [NOTIFICATION_TYPES.INFO]: icon || 'ℹ️'
        };

        let html = `
            <div class="notification-content">
                <div class="notification-icon">${icons[type]}</div>
                <div class="notification-text">
                    ${title ? `<div class="notification-title">${title}</div>` : ''}
                    <div class="notification-message">${message}</div>
                </div>
            </div>
        `;

        // Add action buttons
        if (actions.length > 0) {
            html += '<div class="notification-actions">';
            actions.forEach(action => {
                html += `<button class="notification-action ${action.className || ''}" data-action="${action.id}">${action.label}</button>`;
            });
            html += '</div>';
        }

        // Add close button
        if (closeButton) {
            html += '<button class="notification-close" aria-label="Close notification">×</button>';
        }

        // Add progress bar
        if (progressBar && options.duration > 0) {
            html += '<div class="notification-progress"><div class="notification-progress-bar"></div></div>';
        }

        notification.innerHTML = html;
        return notification;
    }

    /**
     * Show a notification
     * @param {Object} options - Notification options
     * @returns {string} Notification ID
     */
    function showNotification(options = {}) {
        const config = { ...defaultConfig, ...options };
        const id = options.id || `notification-${++notificationCounter}`;

        ensureContainer();

        // Remove existing notification with same ID
        if (notifications.has(id)) {
            removeNotification(id);
        }

        // Limit number of notifications
        if (notifications.size >= config.maxNotifications) {
            const oldestId = notifications.keys().next().value;
            removeNotification(oldestId);
        }

        const notification = createNotificationElement(config);
        notification.dataset.id = id;

        // Position container
        container.className = `notification-container notification-container-${config.position}`;

        // Add to container
        container.appendChild(notification);

        // Store notification data
        notifications.set(id, {
            element: notification,
            config,
            timer: null,
            startTime: Date.now()
        });

        // Animate in
        requestAnimationFrame(() => {
            notification.classList.add('notification-show');
        });

        // Setup event listeners
        setupNotificationEvents(id);

        // Auto-remove after duration
        if (config.duration > 0) {
            startTimer(id);
        }

        // Play sound if enabled
        if (config.sound && typeof config.sound === 'function') {
            config.sound(config.type);
        }

        console.info(`📢 Notification shown: ${id} (${config.type})`);
        return id;
    }

    /**
     * Setup event listeners for a notification
     * @param {string} id - Notification ID
     */
    function setupNotificationEvents(id) {
        const notificationData = notifications.get(id);
        if (!notificationData) return;

        const { element, config } = notificationData;

        // Close button
        const closeButton = element.querySelector('.notification-close');
        if (closeButton) {
            closeButton.addEventListener('click', () => removeNotification(id));
        }

        // Action buttons
        element.querySelectorAll('.notification-action').forEach(button => {
            button.addEventListener('click', (e) => {
                const actionId = e.target.dataset.action;
                const action = config.actions?.find(a => a.id === actionId);
                if (action && action.handler) {
                    action.handler();
                }
                if (!action?.keepOpen) {
                    removeNotification(id);
                }
            });
        });

        // Pause on hover
        if (config.pauseOnHover && config.duration > 0) {
            element.addEventListener('mouseenter', () => pauseTimer(id));
            element.addEventListener('mouseleave', () => resumeTimer(id));
        }

        // Click to dismiss
        element.addEventListener('click', (e) => {
            if (!e.target.closest('.notification-action, .notification-close')) {
                removeNotification(id);
            }
        });

        // Keyboard navigation
        element.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                removeNotification(id);
            }
        });
    }

    /**
     * Start auto-remove timer for notification
     * @param {string} id - Notification ID
     */
    function startTimer(id) {
        const notificationData = notifications.get(id);
        if (!notificationData) return;

        const { config, element } = notificationData;
        const progressBar = element.querySelector('.notification-progress-bar');

        if (progressBar) {
            progressBar.style.animationDuration = `${config.duration}ms`;
            progressBar.style.animationPlayState = 'running';
        }

        notificationData.timer = setTimeout(() => {
            removeNotification(id);
        }, config.duration);

        notificationData.startTime = Date.now();
    }

    /**
     * Pause timer for notification
     * @param {string} id - Notification ID
     */
    function pauseTimer(id) {
        const notificationData = notifications.get(id);
        if (!notificationData || !notificationData.timer) return;

        clearTimeout(notificationData.timer);
        notificationData.timer = null;

        const progressBar = notificationData.element.querySelector('.notification-progress-bar');
        if (progressBar) {
            progressBar.style.animationPlayState = 'paused';
        }

        // Calculate remaining time
        const elapsed = Date.now() - notificationData.startTime;
        notificationData.remainingTime = Math.max(0, notificationData.config.duration - elapsed);
    }

    /**
     * Resume timer for notification
     * @param {string} id - Notification ID
     */
    function resumeTimer(id) {
        const notificationData = notifications.get(id);
        if (!notificationData || notificationData.timer) return;

        const remainingTime = notificationData.remainingTime || notificationData.config.duration;

        const progressBar = notificationData.element.querySelector('.notification-progress-bar');
        if (progressBar) {
            progressBar.style.animationDuration = `${remainingTime}ms`;
            progressBar.style.animationPlayState = 'running';
        }

        notificationData.timer = setTimeout(() => {
            removeNotification(id);
        }, remainingTime);

        notificationData.startTime = Date.now();
    }

    /**
     * Remove a notification
     * @param {string} id - Notification ID
     */
    function removeNotification(id) {
        const notificationData = notifications.get(id);
        if (!notificationData) return;

        const { element, timer } = notificationData;

        if (timer) {
            clearTimeout(timer);
        }

        // Animate out
        element.classList.add('notification-hide');
        
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            notifications.delete(id);

            // Remove container if empty
            if (notifications.size === 0 && container) {
                container.remove();
                container = null;
            }
        }, 300);

        console.info(`📢 Notification removed: ${id}`);
    }

    /**
     * Remove all notifications
     */
    function removeAll() {
        notifications.forEach((_, id) => removeNotification(id));
    }

    /**
     * Update notification content
     * @param {string} id - Notification ID
     * @param {Object} updates - Updates to apply
     */
    function updateNotification(id, updates) {
        const notificationData = notifications.get(id);
        if (!notificationData) return false;

        const { element } = notificationData;

        if (updates.title) {
            const titleElement = element.querySelector('.notification-title');
            if (titleElement) {
                titleElement.textContent = updates.title;
            }
        }

        if (updates.message) {
            const messageElement = element.querySelector('.notification-message');
            if (messageElement) {
                messageElement.textContent = updates.message;
            }
        }

        if (updates.type) {
            element.className = element.className.replace(/notification-\w+/, `notification-${updates.type}`);
        }

        return true;
    }

    // Convenience methods
    const success = (message, options = {}) => showNotification({
        ...options,
        type: NOTIFICATION_TYPES.SUCCESS,
        message
    });

    const error = (message, options = {}) => showNotification({
        ...options,
        type: NOTIFICATION_TYPES.ERROR,
        message,
        duration: options.duration || 0 // Errors don't auto-dismiss by default
    });

    const warning = (message, options = {}) => showNotification({
        ...options,
        type: NOTIFICATION_TYPES.WARNING,
        message
    });

    const info = (message, options = {}) => showNotification({
        ...options,
        type: NOTIFICATION_TYPES.INFO,
        message
    });

    // Export API
    Object.assign(window.Notifications, {
        TYPES: NOTIFICATION_TYPES,
        POSITIONS,
        show: showNotification,
        remove: removeNotification,
        removeAll,
        update: updateNotification,
        success,
        error,
        warning,
        info
    });

    // Initialize styles
    function initializeStyles() {
        if (document.getElementById('notification-styles')) return;

        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .notification-container {
                position: fixed;
                z-index: 1100;
                pointer-events: none;
                max-width: 420px;
                width: 100%;
            }
            
            .notification-container-top-right {
                top: 1rem;
                right: 1rem;
            }
            
            .notification-container-top-left {
                top: 1rem;
                left: 1rem;
            }
            
            .notification-container-top-center {
                top: 1rem;
                left: 50%;
                transform: translateX(-50%);
            }
            
            .notification-container-bottom-right {
                bottom: 1rem;
                right: 1rem;
            }
            
            .notification-container-bottom-left {
                bottom: 1rem;
                left: 1rem;
            }
            
            .notification-container-bottom-center {
                bottom: 1rem;
                left: 50%;
                transform: translateX(-50%);
            }
            
            .notification {
                pointer-events: auto;
                margin-bottom: 0.75rem;
                min-width: 300px;
                max-width: 420px;
                background: white;
                border-radius: 0.75rem;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                border-left: 4px solid;
                position: relative;
                overflow: hidden;
                opacity: 0;
                transform: translateX(100%);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .notification-show {
                opacity: 1;
                transform: translateX(0);
            }
            
            .notification-hide {
                opacity: 0;
                transform: translateX(100%);
            }
            
            .notification-container-top-left .notification-hide,
            .notification-container-bottom-left .notification-hide {
                transform: translateX(-100%);
            }
            
            .notification-content {
                display: flex;
                align-items: flex-start;
                padding: 1rem;
                gap: 0.75rem;
            }
            
            .notification-icon {
                font-size: 1.25rem;
                flex-shrink: 0;
                margin-top: 0.125rem;
            }
            
            .notification-text {
                flex: 1;
                min-width: 0;
            }
            
            .notification-title {
                font-weight: 600;
                font-size: 0.875rem;
                color: var(--gray-900);
                margin-bottom: 0.25rem;
            }
            
            .notification-message {
                font-size: 0.875rem;
                color: var(--gray-700);
                line-height: 1.4;
                word-wrap: break-word;
            }
            
            .notification-actions {
                padding: 0 1rem 1rem;
                display: flex;
                gap: 0.5rem;
            }
            
            .notification-action {
                padding: 0.375rem 0.75rem;
                font-size: 0.75rem;
                font-weight: 500;
                border-radius: 0.375rem;
                border: 1px solid var(--gray-300);
                background: white;
                color: var(--gray-700);
                cursor: pointer;
                transition: all 0.15s ease;
            }
            
            .notification-action:hover {
                background: var(--gray-50);
                border-color: var(--gray-400);
            }
            
            .notification-action.primary {
                background: var(--primary-600);
                color: white;
                border-color: var(--primary-600);
            }
            
            .notification-action.primary:hover {
                background: var(--primary-700);
                border-color: var(--primary-700);
            }
            
            .notification-close {
                position: absolute;
                top: 0.5rem;
                right: 0.5rem;
                width: 1.5rem;
                height: 1.5rem;
                background: none;
                border: none;
                color: var(--gray-400);
                cursor: pointer;
                font-size: 1.125rem;
                line-height: 1;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 0.25rem;
                transition: all 0.15s ease;
            }
            
            .notification-close:hover {
                color: var(--gray-600);
                background: var(--gray-100);
            }
            
            .notification-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: rgba(255, 255, 255, 0.3);
            }
            
            .notification-progress-bar {
                height: 100%;
                width: 100%;
                background: currentColor;
                transform-origin: left;
                animation: notification-progress linear forwards;
            }
            
            @keyframes notification-progress {
                from { transform: scaleX(1); }
                to { transform: scaleX(0); }
            }
            
            .notification-success {
                border-left-color: var(--success-500);
                color: var(--success-600);
            }
            
            .notification-error {
                border-left-color: var(--error-500);
                color: var(--error-600);
            }
            
            .notification-warning {
                border-left-color: var(--warning-500);
                color: var(--warning-600);
            }
            
            .notification-info {
                border-left-color: var(--info-500);
                color: var(--info-600);
            }
            
            /* Dark theme support */
            [data-theme="dark"] .notification {
                background: var(--gray-800);
                border-color: var(--gray-700);
            }
            
            [data-theme="dark"] .notification-title {
                color: var(--gray-100);
            }
            
            [data-theme="dark"] .notification-message {
                color: var(--gray-300);
            }
            
            [data-theme="dark"] .notification-action {
                background: var(--gray-700);
                color: var(--gray-200);
                border-color: var(--gray-600);
            }
            
            [data-theme="dark"] .notification-action:hover {
                background: var(--gray-600);
                border-color: var(--gray-500);
            }
            
            [data-theme="dark"] .notification-close {
                color: var(--gray-500);
            }
            
            [data-theme="dark"] .notification-close:hover {
                color: var(--gray-300);
                background: var(--gray-700);
            }
            
            /* Mobile responsive */
            @media (max-width: 640px) {
                .notification-container {
                    left: 1rem !important;
                    right: 1rem !important;
                    max-width: none;
                    transform: none !important;
                }
                
                .notification {
                    min-width: auto;
                    max-width: none;
                }
            }
        `;

        document.head.appendChild(style);
        console.info('🎨 Notification styles loaded');
    }

    // Initialize styles when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeStyles);
    } else {
        initializeStyles();
    }

})(window);