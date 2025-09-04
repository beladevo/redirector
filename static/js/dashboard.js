/**
 * Redirector Dashboard - Enhanced Interactivity
 * Additional features and improvements for the dashboard
 */

(function(window) {
    'use strict';

    // Create namespace
    window.DashboardEnhancements = window.DashboardEnhancements || {};

    let isInitialized = false;
    let resizeObserver = null;
    let intersectionObserver = null;

    /**
     * Initialize dashboard enhancements
     */
    function initialize() {
        if (isInitialized) return;
        
        console.info('🚀 Initializing dashboard enhancements...');
        
        setupKeyboardShortcuts();
        setupTableEnhancements();
        setupFormEnhancements();
        setupAnimationObserver();
        setupResponsiveHelpers();
        setupAccessibilityEnhancements();
        setupPerformanceMonitoring();
        setupDataVisualizationHelpers();
        
        isInitialized = true;
        console.info('✅ Dashboard enhancements initialized');
    }

    /**
     * Setup global keyboard shortcuts
     */
    function setupKeyboardShortcuts() {
        const shortcuts = {
            'r': () => refreshPage(),
            'f': () => focusSearch(),
            'Escape': () => closeModals(),
            '?': () => showShortcutsHelp(),
            't': () => toggleTheme(),
            'c': () => clearFilters(),
            'e': () => showExportMenu()
        };

        document.addEventListener('keydown', (event) => {
            // Ignore if user is typing in an input
            if (event.target.matches('input, textarea, select, [contenteditable]')) {
                return;
            }

            const key = event.key.toLowerCase();
            const shortcut = shortcuts[key];
            
            if (shortcut && !event.ctrlKey && !event.metaKey && !event.altKey) {
                event.preventDefault();
                shortcut();
            }
        });

        console.info('⌨️ Keyboard shortcuts enabled');
    }

    /**
     * Refresh the page data
     */
    function refreshPage() {
        const refreshButton = document.querySelector('[data-refresh], [x-text*="Refresh"], button:contains("Refresh")');
        if (refreshButton) {
            refreshButton.click();
            if (window.Notifications) {
                window.Notifications.info('Refreshing dashboard data...');
            }
        }
    }

    /**
     * Focus on search input
     */
    function focusSearch() {
        const searchInputs = document.querySelectorAll(
            'input[type="search"], [placeholder*="search" i], [placeholder*="filter" i], [data-search]'
        );
        if (searchInputs.length > 0) {
            searchInputs[0].focus();
            searchInputs[0].select();
        }
    }

    /**
     * Close all open modals
     */
    function closeModals() {
        const openModals = document.querySelectorAll('.modal-overlay[style*="display: block"], .modal-overlay[x-show="true"]');
        openModals.forEach(modal => {
            const closeButton = modal.querySelector('.modal-close, [data-close]');
            if (closeButton) {
                closeButton.click();
            }
        });
    }

    /**
     * Toggle theme if available
     */
    function toggleTheme() {
        if (window.ThemeToggle) {
            window.ThemeToggle.toggleTheme();
        }
    }

    /**
     * Clear all filters
     */
    function clearFilters() {
        const clearButton = document.querySelector('[data-clear-filters], button:contains("Clear Filters")');
        if (clearButton) {
            clearButton.click();
            if (window.Notifications) {
                window.Notifications.success('Filters cleared');
            }
        }
    }

    /**
     * Show export menu
     */
    function showExportMenu() {
        const exportButtons = document.querySelectorAll('[data-export], button:contains("Export")');
        if (exportButtons.length > 0) {
            exportButtons[0].focus();
        }
    }

    /**
     * Show keyboard shortcuts help
     */
    function showShortcutsHelp() {
        if (window.Notifications) {
            window.Notifications.info(
                'Keyboard Shortcuts',
                {
                    title: 'Available Shortcuts',
                    message: `
                        R - Refresh data
                        F - Focus search
                        T - Toggle theme
                        C - Clear filters
                        E - Export menu
                        ? - Show this help
                        ESC - Close modals
                    `,
                    duration: 8000,
                    actions: [{
                        id: 'dismiss',
                        label: 'Got it',
                        className: 'primary'
                    }]
                }
            );
        }
    }

    /**
     * Enhanced table functionality
     */
    function setupTableEnhancements() {
        // Add table utilities
        document.querySelectorAll('.table').forEach(table => {
            enhanceTable(table);
        });

        // Observe for new tables
        if (window.MutationObserver) {
            const observer = new MutationObserver(mutations => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) {
                            const tables = node.matches?.('.table') ? [node] : node.querySelectorAll?.('.table') || [];
                            tables.forEach(enhanceTable);
                        }
                    });
                });
            });

            observer.observe(document.body, { childList: true, subtree: true });
        }
    }

    /**
     * Enhance a single table
     * @param {HTMLElement} table - Table element
     */
    function enhanceTable(table) {
        if (table.dataset.enhanced) return;

        // Add row hover effects
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.addEventListener('mouseenter', () => {
                row.style.backgroundColor = 'var(--gray-50)';
            });
            
            row.addEventListener('mouseleave', () => {
                row.style.backgroundColor = '';
            });
        });

        // Add column sorting (if not already implemented)
        const headers = table.querySelectorAll('th[data-sort]');
        headers.forEach(header => {
            if (header.dataset.sortEnabled) return;
            
            header.style.cursor = 'pointer';
            header.innerHTML += ' <span class="sort-indicator">↕️</span>';
            
            header.addEventListener('click', () => {
                sortTableByColumn(table, header);
            });
            
            header.dataset.sortEnabled = 'true';
        });

        // Add row selection (if checkbox column exists)
        const checkboxes = table.querySelectorAll('input[type="checkbox"]');
        if (checkboxes.length > 0) {
            setupTableSelection(table, checkboxes);
        }

        table.dataset.enhanced = 'true';
    }

    /**
     * Sort table by column
     * @param {HTMLElement} table - Table element
     * @param {HTMLElement} header - Header element
     */
    function sortTableByColumn(table, header) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const columnIndex = Array.from(header.parentNode.children).indexOf(header);
        const currentSort = header.dataset.sortDirection || 'none';
        
        // Reset other headers
        table.querySelectorAll('th[data-sort]').forEach(h => {
            if (h !== header) {
                h.dataset.sortDirection = 'none';
                const indicator = h.querySelector('.sort-indicator');
                if (indicator) indicator.textContent = '↕️';
            }
        });

        let newSort;
        if (currentSort === 'none' || currentSort === 'desc') {
            newSort = 'asc';
        } else {
            newSort = 'desc';
        }

        rows.sort((a, b) => {
            const aValue = a.cells[columnIndex]?.textContent.trim() || '';
            const bValue = b.cells[columnIndex]?.textContent.trim() || '';
            
            // Try to parse as numbers
            const aNum = parseFloat(aValue);
            const bNum = parseFloat(bValue);
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return newSort === 'asc' ? aNum - bNum : bNum - aNum;
            }
            
            // Sort as strings
            return newSort === 'asc' 
                ? aValue.localeCompare(bValue)
                : bValue.localeCompare(aValue);
        });

        // Update DOM
        rows.forEach(row => tbody.appendChild(row));
        
        // Update header
        header.dataset.sortDirection = newSort;
        const indicator = header.querySelector('.sort-indicator');
        if (indicator) {
            indicator.textContent = newSort === 'asc' ? '↑' : '↓';
        }
    }

    /**
     * Setup table row selection
     * @param {HTMLElement} table - Table element
     * @param {NodeList} checkboxes - Checkbox elements
     */
    function setupTableSelection(table, checkboxes) {
        const headerCheckbox = table.querySelector('thead input[type="checkbox"]');
        const rowCheckboxes = table.querySelectorAll('tbody input[type="checkbox"]');

        if (headerCheckbox) {
            headerCheckbox.addEventListener('change', () => {
                const isChecked = headerCheckbox.checked;
                rowCheckboxes.forEach(checkbox => {
                    checkbox.checked = isChecked;
                    updateRowSelection(checkbox);
                });
            });
        }

        rowCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                updateRowSelection(checkbox);
                
                // Update header checkbox
                if (headerCheckbox) {
                    const checkedCount = table.querySelectorAll('tbody input[type="checkbox"]:checked').length;
                    headerCheckbox.checked = checkedCount === rowCheckboxes.length;
                    headerCheckbox.indeterminate = checkedCount > 0 && checkedCount < rowCheckboxes.length;
                }
            });
        });
    }

    /**
     * Update row selection appearance
     * @param {HTMLElement} checkbox - Checkbox element
     */
    function updateRowSelection(checkbox) {
        const row = checkbox.closest('tr');
        if (row) {
            row.classList.toggle('selected', checkbox.checked);
            row.style.backgroundColor = checkbox.checked ? 'var(--primary-50)' : '';
        }
    }

    /**
     * Enhanced form functionality
     */
    function setupFormEnhancements() {
        // Auto-save form data to localStorage
        const forms = document.querySelectorAll('form[data-autosave]');
        forms.forEach(setupFormAutosave);

        // Add validation enhancements
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(setupInputEnhancements);
    }

    /**
     * Setup form autosave
     * @param {HTMLElement} form - Form element
     */
    function setupFormAutosave(form) {
        const formId = form.id || form.dataset.autosave;
        if (!formId) return;

        const storageKey = `form-autosave-${formId}`;

        // Load saved data
        const savedData = window.RedirectorUtils?.storage.get(storageKey);
        if (savedData) {
            Object.entries(savedData).forEach(([name, value]) => {
                const input = form.querySelector(`[name="${name}"]`);
                if (input && input.type !== 'password') {
                    input.value = value;
                }
            });
        }

        // Save data on change
        const saveData = window.RedirectorUtils?.debounce(() => {
            const formData = new FormData(form);
            const data = {};
            formData.forEach((value, key) => {
                data[key] = value;
            });
            window.RedirectorUtils?.storage.set(storageKey, data);
        }, 1000);

        form.addEventListener('input', saveData);
        form.addEventListener('change', saveData);

        // Clear on submit
        form.addEventListener('submit', () => {
            window.RedirectorUtils?.storage.remove(storageKey);
        });
    }

    /**
     * Setup input enhancements
     * @param {HTMLElement} input - Input element
     */
    function setupInputEnhancements(input) {
        // Add floating label effect
        if (input.placeholder && !input.dataset.noFloatingLabel) {
            addFloatingLabel(input);
        }

        // Add character counter for textarea
        if (input.tagName === 'TEXTAREA' && input.maxLength) {
            addCharacterCounter(input);
        }

        // Add URL validation indicator
        if (input.type === 'url') {
            addUrlValidation(input);
        }
    }

    /**
     * Add floating label effect
     * @param {HTMLElement} input - Input element
     */
    function addFloatingLabel(input) {
        const container = input.parentElement;
        if (!container.classList.contains('form-group')) return;

        const label = container.querySelector('label');
        if (!label) return;

        // Add CSS classes
        container.classList.add('floating-label');
        
        const updateLabel = () => {
            container.classList.toggle('has-value', input.value.length > 0);
            container.classList.toggle('is-focused', document.activeElement === input);
        };

        input.addEventListener('focus', updateLabel);
        input.addEventListener('blur', updateLabel);
        input.addEventListener('input', updateLabel);

        updateLabel();
    }

    /**
     * Add character counter
     * @param {HTMLElement} textarea - Textarea element
     */
    function addCharacterCounter(textarea) {
        const counter = document.createElement('div');
        counter.className = 'character-counter';
        counter.textContent = `0 / ${textarea.maxLength}`;

        textarea.parentElement.appendChild(counter);

        const updateCounter = () => {
            const current = textarea.value.length;
            const max = textarea.maxLength;
            counter.textContent = `${current} / ${max}`;
            counter.classList.toggle('over-limit', current > max * 0.9);
        };

        textarea.addEventListener('input', updateCounter);
        updateCounter();
    }

    /**
     * Add URL validation
     * @param {HTMLElement} input - URL input element
     */
    function addUrlValidation(input) {
        const indicator = document.createElement('div');
        indicator.className = 'url-validation-indicator';
        
        input.parentElement.style.position = 'relative';
        input.parentElement.appendChild(indicator);

        const validateUrl = () => {
            const isValid = window.RedirectorUtils?.isValidUrl(input.value) || false;
            indicator.textContent = input.value ? (isValid ? '✓' : '✗') : '';
            indicator.className = `url-validation-indicator ${isValid ? 'valid' : 'invalid'}`;
            input.classList.toggle('invalid', input.value && !isValid);
        };

        input.addEventListener('input', validateUrl);
        input.addEventListener('blur', validateUrl);
    }

    /**
     * Setup animation observer for performance
     */
    function setupAnimationObserver() {
        if (!window.IntersectionObserver) return;

        intersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                } else {
                    entry.target.classList.remove('animate-in');
                }
            });
        }, {
            rootMargin: '50px'
        });

        // Observe elements with animation classes
        document.querySelectorAll('[data-animate]').forEach(element => {
            intersectionObserver.observe(element);
        });
    }

    /**
     * Setup responsive helpers
     */
    function setupResponsiveHelpers() {
        if (!window.ResizeObserver) return;

        resizeObserver = new ResizeObserver(entries => {
            entries.forEach(entry => {
                const element = entry.target;
                const width = entry.contentRect.width;

                // Add responsive classes
                element.classList.toggle('is-mobile', width < 640);
                element.classList.toggle('is-tablet', width >= 640 && width < 1024);
                element.classList.toggle('is-desktop', width >= 1024);
            });
        });

        // Observe main container
        const mainContainer = document.querySelector('.dashboard-main, main, [data-responsive]');
        if (mainContainer) {
            resizeObserver.observe(mainContainer);
        }
    }

    /**
     * Setup accessibility enhancements
     */
    function setupAccessibilityEnhancements() {
        // Add focus indicators for keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });

        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });

        // Add aria-labels to icon-only buttons
        document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])').forEach(button => {
            const text = button.textContent.trim();
            const icon = button.querySelector('[class*="icon"], svg, img');
            
            if (icon && !text) {
                // Try to infer label from context
                const title = button.title || button.dataset.title;
                if (title) {
                    button.setAttribute('aria-label', title);
                }
            }
        });

        // Improve table accessibility
        document.querySelectorAll('table').forEach(table => {
            if (!table.getAttribute('role')) {
                table.setAttribute('role', 'table');
            }
            
            // Add scope attributes to headers
            table.querySelectorAll('th').forEach(th => {
                if (!th.getAttribute('scope')) {
                    th.setAttribute('scope', 'col');
                }
            });
        });
    }

    /**
     * Setup performance monitoring
     */
    function setupPerformanceMonitoring() {
        if (!window.performance || !console.info) return;

        // Monitor page load time
        window.addEventListener('load', () => {
            const perfData = window.performance.timing;
            const loadTime = perfData.loadEventEnd - perfData.navigationStart;
            console.info(`📊 Page load time: ${loadTime}ms`);
        });

        // Monitor long tasks (if API available)
        if ('PerformanceObserver' in window) {
            try {
                const longTaskObserver = new PerformanceObserver(list => {
                    list.getEntries().forEach(entry => {
                        if (entry.duration > 50) {
                            console.warn(`⚠️ Long task detected: ${entry.duration}ms`);
                        }
                    });
                });
                longTaskObserver.observe({ entryTypes: ['longtask'] });
            } catch (e) {
                // Long task API not supported
            }
        }
    }

    /**
     * Setup data visualization helpers
     */
    function setupDataVisualizationHelpers() {
        // Add sparkline charts to numeric data
        document.querySelectorAll('[data-sparkline]').forEach(element => {
            createSparkline(element);
        });

        // Add progress bars to percentage data
        document.querySelectorAll('[data-progress]').forEach(element => {
            createProgressBar(element);
        });
    }

    /**
     * Create a simple sparkline chart
     * @param {HTMLElement} element - Element to add sparkline to
     */
    function createSparkline(element) {
        const data = element.dataset.sparkline.split(',').map(Number);
        if (data.length < 2) return;

        const max = Math.max(...data);
        const min = Math.min(...data);
        const range = max - min || 1;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '60');
        svg.setAttribute('height', '20');
        svg.className = 'sparkline';

        const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
        const points = data.map((value, index) => {
            const x = (index / (data.length - 1)) * 58 + 1;
            const y = 19 - ((value - min) / range) * 18;
            return `${x},${y}`;
        }).join(' ');

        polyline.setAttribute('points', points);
        polyline.setAttribute('fill', 'none');
        polyline.setAttribute('stroke', 'currentColor');
        polyline.setAttribute('stroke-width', '1.5');

        svg.appendChild(polyline);
        element.appendChild(svg);
    }

    /**
     * Create a progress bar
     * @param {HTMLElement} element - Element to add progress bar to
     */
    function createProgressBar(element) {
        const value = parseInt(element.dataset.progress) || 0;
        const max = parseInt(element.dataset.progressMax) || 100;
        const percentage = Math.min((value / max) * 100, 100);

        const progressBar = document.createElement('div');
        progressBar.className = 'progress-bar-container';
        progressBar.innerHTML = `
            <div class="progress-bar" style="width: ${percentage}%"></div>
            <span class="progress-text">${value}/${max}</span>
        `;

        element.appendChild(progressBar);
    }

    /**
     * Cleanup function
     */
    function cleanup() {
        if (resizeObserver) {
            resizeObserver.disconnect();
        }
        if (intersectionObserver) {
            intersectionObserver.disconnect();
        }
    }

    // Export API
    Object.assign(window.DashboardEnhancements, {
        initialize,
        cleanup
    });

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', cleanup);

})(window);

// Add enhancement styles
(function() {
    'use strict';
    
    const style = document.createElement('style');
    style.id = 'dashboard-enhancement-styles';
    style.textContent = `
        /* Keyboard navigation indicators */
        .keyboard-navigation button:focus,
        .keyboard-navigation a:focus,
        .keyboard-navigation input:focus,
        .keyboard-navigation textarea:focus,
        .keyboard-navigation select:focus {
            outline: 2px solid var(--primary-600) !important;
            outline-offset: 2px !important;
        }
        
        /* Table enhancements */
        .table tbody tr.selected {
            background-color: var(--primary-50) !important;
        }
        
        .sort-indicator {
            font-size: 0.75em;
            margin-left: 0.25rem;
            opacity: 0.7;
        }
        
        /* Floating labels */
        .floating-label {
            position: relative;
        }
        
        .floating-label label {
            position: absolute;
            left: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            transition: all 0.2s ease;
            pointer-events: none;
            color: var(--gray-500);
            background: white;
            padding: 0 0.25rem;
        }
        
        .floating-label.has-value label,
        .floating-label.is-focused label {
            top: 0;
            font-size: 0.75rem;
            color: var(--primary-600);
        }
        
        /* Character counter */
        .character-counter {
            font-size: 0.75rem;
            color: var(--gray-500);
            text-align: right;
            margin-top: 0.25rem;
        }
        
        .character-counter.over-limit {
            color: var(--warning-600);
        }
        
        /* URL validation */
        .url-validation-indicator {
            position: absolute;
            right: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            font-weight: bold;
        }
        
        .url-validation-indicator.valid {
            color: var(--success-600);
        }
        
        .url-validation-indicator.invalid {
            color: var(--error-600);
        }
        
        input.invalid {
            border-color: var(--error-500);
        }
        
        /* Sparkline charts */
        .sparkline {
            display: inline-block;
            vertical-align: middle;
            margin-left: 0.5rem;
        }
        
        /* Progress bars */
        .progress-bar-container {
            position: relative;
            background: var(--gray-200);
            border-radius: 0.25rem;
            height: 1rem;
            margin-top: 0.25rem;
            overflow: hidden;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, var(--primary-500), var(--primary-600));
            border-radius: inherit;
            transition: width 0.3s ease;
        }
        
        .progress-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--gray-700);
            text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8);
        }
        
        /* Animation helpers */
        [data-animate] {
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.6s ease;
        }
        
        [data-animate].animate-in {
            opacity: 1;
            transform: translateY(0);
        }
        
        /* Responsive helpers */
        .is-mobile .hide-mobile,
        .is-tablet .hide-tablet,
        .is-desktop .hide-desktop {
            display: none !important;
        }
    `;
    
    document.head.appendChild(style);
})();