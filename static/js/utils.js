/**
 * Redirector Dashboard - Utility Functions
 * Modern JavaScript utilities for enhanced functionality
 */

(function(window) {
    'use strict';

    // Create namespace
    window.RedirectorUtils = window.RedirectorUtils || {};

    /**
     * Debounce function to limit the rate of function calls
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in milliseconds
     * @param {boolean} immediate - Execute immediately
     * @returns {Function} Debounced function
     */
    function debounce(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    }

    /**
     * Throttle function to limit the rate of function calls
     * @param {Function} func - Function to throttle
     * @param {number} limit - Time limit in milliseconds
     * @returns {Function} Throttled function
     */
    function throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * Format bytes to human-readable format
     * @param {number} bytes - Bytes to format
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted string
     */
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    /**
     * Format duration in milliseconds to human-readable format
     * @param {number} ms - Milliseconds
     * @returns {string} Formatted duration
     */
    function formatDuration(ms) {
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
        return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
    }

    /**
     * Format relative time (time ago)
     * @param {Date|string} date - Date to format
     * @returns {string} Relative time string
     */
    function formatRelativeTime(date) {
        const now = new Date();
        const target = new Date(date);
        const diffMs = now - target;
        
        const diffSec = Math.floor(diffMs / 1000);
        const diffMin = Math.floor(diffSec / 60);
        const diffHour = Math.floor(diffMin / 60);
        const diffDay = Math.floor(diffHour / 24);
        
        if (diffSec < 60) return 'just now';
        if (diffMin < 60) return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
        if (diffHour < 24) return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
        if (diffDay < 7) return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
        
        return target.toLocaleDateString();
    }

    /**
     * Copy text to clipboard
     * @param {string} text - Text to copy
     * @returns {Promise<boolean>} Success status
     */
    async function copyToClipboard(text) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                return true;
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                const result = document.execCommand('copy');
                textArea.remove();
                return result;
            }
        } catch (error) {
            console.error('Failed to copy to clipboard:', error);
            return false;
        }
    }

    /**
     * Generate a random ID
     * @param {number} length - Length of the ID
     * @returns {string} Random ID
     */
    function generateId(length = 8) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    /**
     * Validate email address
     * @param {string} email - Email to validate
     * @returns {boolean} Is valid email
     */
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Validate URL
     * @param {string} url - URL to validate
     * @returns {boolean} Is valid URL
     */
    function isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Escape HTML to prevent XSS
     * @param {string} html - HTML string to escape
     * @returns {string} Escaped HTML
     */
    function escapeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }

    /**
     * Parse query parameters from URL
     * @param {string} url - URL to parse (defaults to current URL)
     * @returns {Object} Query parameters object
     */
    function parseQueryParams(url = window.location.href) {
        const params = {};
        const urlObj = new URL(url);
        
        for (const [key, value] of urlObj.searchParams) {
            if (params[key]) {
                // Handle multiple values for same key
                if (Array.isArray(params[key])) {
                    params[key].push(value);
                } else {
                    params[key] = [params[key], value];
                }
            } else {
                params[key] = value;
            }
        }
        
        return params;
    }

    /**
     * Build query string from object
     * @param {Object} params - Parameters object
     * @returns {string} Query string
     */
    function buildQueryString(params) {
        const query = new URLSearchParams();
        
        for (const [key, value] of Object.entries(params)) {
            if (Array.isArray(value)) {
                value.forEach(v => query.append(key, v));
            } else if (value !== null && value !== undefined && value !== '') {
                query.append(key, value);
            }
        }
        
        return query.toString();
    }

    /**
     * Detect user's preferred color scheme
     * @returns {string} 'light' or 'dark'
     */
    function getPreferredColorScheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    /**
     * Local storage helpers with error handling
     */
    const storage = {
        /**
         * Get item from localStorage
         * @param {string} key - Storage key
         * @param {*} defaultValue - Default value if key doesn't exist
         * @returns {*} Stored value or default
         */
        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (error) {
                console.warn('Failed to get from localStorage:', error);
                return defaultValue;
            }
        },

        /**
         * Set item in localStorage
         * @param {string} key - Storage key
         * @param {*} value - Value to store
         * @returns {boolean} Success status
         */
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (error) {
                console.warn('Failed to set localStorage:', error);
                return false;
            }
        },

        /**
         * Remove item from localStorage
         * @param {string} key - Storage key
         * @returns {boolean} Success status
         */
        remove(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (error) {
                console.warn('Failed to remove from localStorage:', error);
                return false;
            }
        },

        /**
         * Clear all localStorage
         * @returns {boolean} Success status
         */
        clear() {
            try {
                localStorage.clear();
                return true;
            } catch (error) {
                console.warn('Failed to clear localStorage:', error);
                return false;
            }
        }
    };

    /**
     * Device and browser detection
     */
    const device = {
        isMobile: () => /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
        isTablet: () => /iPad|Android(?!.*Mobile)/i.test(navigator.userAgent),
        isDesktop: () => !device.isMobile() && !device.isTablet(),
        isTouch: () => 'ontouchstart' in window || navigator.maxTouchPoints > 0,
        supportsWebP: () => {
            const canvas = document.createElement('canvas');
            canvas.width = 1;
            canvas.height = 1;
            return canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
        }
    };

    /**
     * Performance monitoring helpers
     */
    const performance = {
        /**
         * Measure function execution time
         * @param {Function} fn - Function to measure
         * @param {...*} args - Function arguments
         * @returns {Object} Result and execution time
         */
        measure: async (fn, ...args) => {
            const start = window.performance.now();
            const result = await fn(...args);
            const end = window.performance.now();
            return {
                result,
                executionTime: end - start
            };
        },

        /**
         * Create a performance mark
         * @param {string} name - Mark name
         */
        mark: (name) => {
            if (window.performance && window.performance.mark) {
                window.performance.mark(name);
            }
        },

        /**
         * Measure between two marks
         * @param {string} name - Measure name
         * @param {string} startMark - Start mark name
         * @param {string} endMark - End mark name
         */
        measureBetween: (name, startMark, endMark) => {
            if (window.performance && window.performance.measure) {
                window.performance.measure(name, startMark, endMark);
            }
        }
    };

    // Export all utilities
    Object.assign(window.RedirectorUtils, {
        debounce,
        throttle,
        formatBytes,
        formatDuration,
        formatRelativeTime,
        copyToClipboard,
        generateId,
        isValidEmail,
        isValidUrl,
        escapeHtml,
        parseQueryParams,
        buildQueryString,
        getPreferredColorScheme,
        storage,
        device,
        performance
    });

    // Initialize utilities when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeUtils);
    } else {
        initializeUtils();
    }

    function initializeUtils() {
        console.info('🔧 Redirector utilities loaded');
        
        // Add global keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + K for search (if search functionality exists)
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                const searchInput = document.querySelector('[data-search]');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Escape key to close modals
            if (event.key === 'Escape') {
                const openModal = document.querySelector('.modal-overlay[style*="display: block"]');
                if (openModal) {
                    const closeButton = openModal.querySelector('.modal-close');
                    if (closeButton) {
                        closeButton.click();
                    }
                }
            }
        });

        // Add copy buttons to code elements
        document.querySelectorAll('pre code, .font-mono').forEach(codeElement => {
            if (codeElement.dataset.noCopy) return;
            
            const container = codeElement.closest('pre') || codeElement;
            if (container.querySelector('.copy-button')) return; // Already has copy button
            
            const copyButton = document.createElement('button');
            copyButton.className = 'copy-button absolute top-2 right-2 bg-gray-800 text-white px-2 py-1 text-xs rounded opacity-0 transition-opacity hover:opacity-100 focus:opacity-100';
            copyButton.textContent = 'Copy';
            copyButton.setAttribute('aria-label', 'Copy code to clipboard');
            
            copyButton.addEventListener('click', async () => {
                const text = codeElement.textContent || codeElement.innerText;
                const success = await copyToClipboard(text);
                
                if (success) {
                    const originalText = copyButton.textContent;
                    copyButton.textContent = 'Copied!';
                    copyButton.classList.add('bg-green-600');
                    
                    setTimeout(() => {
                        copyButton.textContent = originalText;
                        copyButton.classList.remove('bg-green-600');
                    }, 2000);
                }
            });
            
            const wrapper = container.style.position === 'relative' ? container : (() => {
                const div = document.createElement('div');
                div.style.position = 'relative';
                container.parentNode.insertBefore(div, container);
                div.appendChild(container);
                return div;
            })();
            
            wrapper.appendChild(copyButton);
            
            // Show copy button on hover
            wrapper.addEventListener('mouseenter', () => {
                copyButton.classList.remove('opacity-0');
                copyButton.classList.add('opacity-100');
            });
            
            wrapper.addEventListener('mouseleave', () => {
                copyButton.classList.add('opacity-0');
                copyButton.classList.remove('opacity-100');
            });
        });
    }

})(window);