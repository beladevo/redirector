/**
 * Redirector Dashboard - Theme Toggle
 * Modern dark/light mode toggle with smooth transitions
 */

(function(window) {
    'use strict';

    // Create namespace
    window.ThemeToggle = window.ThemeToggle || {};

    const THEME_KEY = 'redirector-theme';
    const THEMES = {
        LIGHT: 'light',
        DARK: 'dark',
        AUTO: 'auto'
    };

    let currentTheme = THEMES.AUTO;
    let prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');

    /**
     * Get the effective theme (resolves 'auto' to actual theme)
     * @returns {string} 'light' or 'dark'
     */
    function getEffectiveTheme() {
        if (currentTheme === THEMES.AUTO) {
            return prefersDarkScheme.matches ? THEMES.DARK : THEMES.LIGHT;
        }
        return currentTheme;
    }

    /**
     * Apply theme to document
     * @param {string} theme - Theme to apply
     */
    function applyTheme(theme) {
        const effectiveTheme = theme === THEMES.AUTO 
            ? (prefersDarkScheme.matches ? THEMES.DARK : THEMES.LIGHT)
            : theme;

        document.documentElement.setAttribute('data-theme', effectiveTheme);
        document.documentElement.classList.toggle('dark-theme', effectiveTheme === THEMES.DARK);
        
        // Update meta theme-color for mobile browsers
        updateMetaThemeColor(effectiveTheme);
        
        console.info(`🎨 Theme applied: ${theme} (effective: ${effectiveTheme})`);
    }

    /**
     * Update meta theme-color for mobile browsers
     * @param {string} theme - Current theme
     */
    function updateMetaThemeColor(theme) {
        let themeColorMeta = document.querySelector('meta[name="theme-color"]');
        
        if (!themeColorMeta) {
            themeColorMeta = document.createElement('meta');
            themeColorMeta.name = 'theme-color';
            document.head.appendChild(themeColorMeta);
        }
        
        // Use CSS custom properties values
        const colors = {
            light: '#ffffff',
            dark: '#1e293b'
        };
        
        themeColorMeta.content = colors[theme];
    }

    /**
     * Set theme and persist to localStorage
     * @param {string} theme - Theme to set
     */
    function setTheme(theme) {
        if (!Object.values(THEMES).includes(theme)) {
            console.warn(`Invalid theme: ${theme}`);
            return;
        }

        currentTheme = theme;
        applyTheme(theme);
        
        // Store theme preference
        if (window.RedirectorUtils && window.RedirectorUtils.storage) {
            window.RedirectorUtils.storage.set(THEME_KEY, theme);
        } else {
            try {
                localStorage.setItem(THEME_KEY, theme);
            } catch (error) {
                console.warn('Failed to save theme preference:', error);
            }
        }

        // Dispatch custom event
        window.dispatchEvent(new CustomEvent('themechange', {
            detail: { theme, effectiveTheme: getEffectiveTheme() }
        }));
    }

    /**
     * Get current theme
     * @returns {string} Current theme
     */
    function getTheme() {
        return currentTheme;
    }

    /**
     * Toggle between light and dark themes
     */
    function toggleTheme() {
        const effectiveTheme = getEffectiveTheme();
        const newTheme = effectiveTheme === THEMES.LIGHT ? THEMES.DARK : THEMES.LIGHT;
        setTheme(newTheme);
    }

    /**
     * Cycle through all themes (light -> dark -> auto)
     */
    function cycleTheme() {
        const themeOrder = [THEMES.LIGHT, THEMES.DARK, THEMES.AUTO];
        const currentIndex = themeOrder.indexOf(currentTheme);
        const nextIndex = (currentIndex + 1) % themeOrder.length;
        setTheme(themeOrder[nextIndex]);
    }

    /**
     * Initialize theme system
     */
    function initializeTheme() {
        // Load saved theme preference
        let savedTheme;
        if (window.RedirectorUtils && window.RedirectorUtils.storage) {
            savedTheme = window.RedirectorUtils.storage.get(THEME_KEY);
        } else {
            try {
                savedTheme = localStorage.getItem(THEME_KEY);
            } catch (error) {
                console.warn('Failed to load theme preference:', error);
            }
        }

        currentTheme = savedTheme || THEMES.AUTO;
        applyTheme(currentTheme);

        // Listen for system theme changes
        prefersDarkScheme.addEventListener('change', (e) => {
            if (currentTheme === THEMES.AUTO) {
                applyTheme(THEMES.AUTO);
            }
        });

        console.info('🎨 Theme system initialized');
    }

    /**
     * Create theme toggle button
     * @param {Object} options - Button options
     * @returns {HTMLElement} Theme toggle button
     */
    function createToggleButton(options = {}) {
        const {
            className = 'theme-toggle-btn',
            position = 'top-right',
            showLabel = false,
            useIcon = true
        } = options;

        const button = document.createElement('button');
        button.className = `${className} btn btn-outline`;
        button.setAttribute('aria-label', 'Toggle theme');
        button.type = 'button';

        // Icons for different themes
        const icons = {
            [THEMES.LIGHT]: '☀️',
            [THEMES.DARK]: '🌙',
            [THEMES.AUTO]: '🔄'
        };

        function updateButton() {
            const theme = getTheme();
            const icon = useIcon ? icons[theme] : '';
            const label = showLabel ? theme.charAt(0).toUpperCase() + theme.slice(1) : '';
            
            button.innerHTML = `${icon} ${label}`.trim();
            button.setAttribute('title', `Current theme: ${theme}`);
        }

        updateButton();

        button.addEventListener('click', () => {
            cycleTheme();
            updateButton();
        });

        // Listen for theme changes from other sources
        window.addEventListener('themechange', updateButton);

        // Position the button if needed
        if (position !== 'none') {
            button.style.position = 'fixed';
            button.style.zIndex = '1000';
            
            switch (position) {
                case 'top-right':
                    button.style.top = '1rem';
                    button.style.right = '1rem';
                    break;
                case 'top-left':
                    button.style.top = '1rem';
                    button.style.left = '1rem';
                    break;
                case 'bottom-right':
                    button.style.bottom = '1rem';
                    button.style.right = '1rem';
                    break;
                case 'bottom-left':
                    button.style.bottom = '1rem';
                    button.style.left = '1rem';
                    break;
            }
        }

        return button;
    }

    /**
     * Add theme classes to specific elements
     * @param {string} selector - CSS selector
     * @param {Object} themeClasses - Object with theme->class mappings
     */
    function addThemeClasses(selector, themeClasses) {
        const elements = document.querySelectorAll(selector);
        
        function updateClasses() {
            const theme = getEffectiveTheme();
            elements.forEach(element => {
                // Remove all theme classes
                Object.values(themeClasses).forEach(className => {
                    element.classList.remove(className);
                });
                
                // Add current theme class
                if (themeClasses[theme]) {
                    element.classList.add(themeClasses[theme]);
                }
            });
        }

        updateClasses();
        window.addEventListener('themechange', updateClasses);
    }

    // Export API
    Object.assign(window.ThemeToggle, {
        THEMES,
        setTheme,
        getTheme,
        getEffectiveTheme,
        toggleTheme,
        cycleTheme,
        createToggleButton,
        addThemeClasses,
        initialize: initializeTheme
    });

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeTheme);
    } else {
        initializeTheme();
    }

})(window);

// Add theme-aware CSS custom properties
(function() {
    'use strict';
    
    const style = document.createElement('style');
    style.textContent = `
        /* Theme transition */
        :root {
            transition: color 0.3s ease, background-color 0.3s ease;
        }
        
        /* Dark theme overrides */
        [data-theme="dark"] {
            --primary-50: #1e3a8a;
            --primary-100: #1e40af;
            --primary-200: #1d4ed8;
            --primary-300: #2563eb;
            --primary-400: #3b82f6;
            --primary-500: #60a5fa;
            --primary-600: #93c5fd;
            --primary-700: #bfdbfe;
            --primary-800: #dbeafe;
            --primary-900: #eff6ff;
            
            --gray-50: #020617;
            --gray-100: #0f172a;
            --gray-200: #1e293b;
            --gray-300: #334155;
            --gray-400: #475569;
            --gray-500: #64748b;
            --gray-600: #94a3b8;
            --gray-700: #cbd5e1;
            --gray-800: #e2e8f0;
            --gray-900: #f1f5f9;
            --gray-950: #f8fafc;
            
            color-scheme: dark;
        }
        
        /* Theme toggle button styles */
        .theme-toggle-btn {
            border-radius: 50%;
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2em;
            backdrop-filter: blur(8px);
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .theme-toggle-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 12px rgba(0, 0, 0, 0.15);
            background: rgba(255, 255, 255, 0.2);
        }
        
        [data-theme="dark"] .theme-toggle-btn {
            background: rgba(0, 0, 0, 0.2);
            border-color: rgba(255, 255, 255, 0.1);
        }
        
        [data-theme="dark"] .theme-toggle-btn:hover {
            background: rgba(0, 0, 0, 0.3);
        }
        
        /* Smooth transitions for theme changes */
        *,
        *::before,
        *::after {
            transition-property: color, background-color, border-color, box-shadow;
            transition-duration: 0.3s;
            transition-timing-function: ease;
        }
        
        /* Preserve transitions that should be faster */
        .loading-spinner,
        [x-transition],
        .transition-transform,
        .transition-opacity {
            transition-duration: var(--transition-default, 150ms) !important;
        }
    `;
    
    document.head.appendChild(style);
})();