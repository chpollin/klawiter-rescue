/**
 * router.js
 * Handles URL routing and browser history
 */

const ZweigRouter = (function() {
    // Current route state
    let _currentRoute = {
        view: 'dashboard', // Set dashboard as default view
        id: null,
        filter: null,
        query: null
    };
    
    // Private methods
    
    /**
     * Parse the URL hash to extract route parameters
     * @returns {Object} Route parameters extracted from the hash
     */
    const _parseHash = function() {
        const hash = window.location.hash.substring(1);
        const params = {};
        
        if (!hash) {
            return params;
        }
        
        // Special case for dashboard
        if (hash === 'dashboard') {
            params.view = 'dashboard';
            return params;
        }
        
        // Split hash parts
        const parts = hash.split('&');
        
        parts.forEach(part => {
            const [key, value] = part.split('=');
            if (key && value) {
                params[key] = decodeURIComponent(value);
            } else if (key) {
                params[key] = true;
            }
        });
        
        return params;
    };
    
    /**
     * Handle route changes
     */
    const _handleRouteChange = function() {
        // Parse the hash
        const params = _parseHash();
        
        // Update current route
        _currentRoute = {
            view: params.view || 'dashboard', // Default to dashboard
            id: params.id || null,
            filter: params.filter || null,
            query: params.query || null
        };
        
        console.log('Route changed:', _currentRoute);
        
        // Handle different routes
        if (_currentRoute.view === 'dashboard') {
            // Dashboard view
            if (ZweigBibliography.isLoaded()) {
                ZweigUI.displayDashboard();
            }
        } else if (_currentRoute.view === 'list') {
            // List view with optional filters
            if (ZweigBibliography.isLoaded()) {
                const filters = {};
                if (_currentRoute.filter && _currentRoute.filter !== 'all') {
                    filters[_currentRoute.filter] = _currentRoute.id;
                }
                
                const entries = ZweigBibliography.searchEntries(_currentRoute.query || '', filters);
                ZweigUI.displayEntries(entries);
            }
        } else if (_currentRoute.view === 'detail') {
            // Detail view
            if (_currentRoute.id) {
                const entry = ZweigBibliography.getEntryById(_currentRoute.id);
                if (entry) {
                    ZweigUI.displayEntryDetail(entry);
                } else {
                    console.error(`Entry with ID ${_currentRoute.id} not found`);
                    ZweigUI.showError(`Entry with ID ${_currentRoute.id} not found`);
                    
                    // Reset to dashboard view
                    window.location.hash = 'dashboard';
                }
            }
        } else if (_currentRoute.view) {
            // Legacy support for direct view by ID
            const entry = ZweigBibliography.getEntryById(_currentRoute.view);
            if (entry) {
                ZweigUI.displayEntryDetail(entry);
            } else {
                console.error(`Entry with ID ${_currentRoute.view} not found`);
                ZweigUI.showError(`Entry with ID ${_currentRoute.view} not found`);
                
                // Reset to dashboard view
                window.location.hash = 'dashboard';
            }
        } else {
            // Default view if no route matches
            window.location.hash = 'dashboard';
        }
        
        // Update active nav link
        _updateNavLinks();
    };
    
    /**
     * Update the active state of navigation links
     */
    const _updateNavLinks = function() {
        const navLinks = document.querySelectorAll('.filter-options a');
        navLinks.forEach(link => {
            link.classList.remove('active');
            
            // Match dashboard view
            if (_currentRoute.view === 'dashboard' && link.dataset.view === 'dashboard') {
                link.classList.add('active');
            }
            // Match list view with specific filter
            else if (_currentRoute.view === 'list' && link.dataset.view === 'list') {
                if ((_currentRoute.filter === link.dataset.filter) || 
                    (_currentRoute.filter === null && link.dataset.filter === 'all')) {
                    link.classList.add('active');
                }
            }
        });
    };
    
    // Return public methods
    return {
        /**
         * Initialize the router
         */
        initialize: function() {
            // Listen for hash changes
            window.addEventListener('hashchange', _handleRouteChange);
            
            // Handle initial route
            ZweigBibliography.addEventListener('loaded', function() {
                // If no hash is set, default to dashboard
                if (!window.location.hash) {
                    window.location.hash = 'dashboard';
                } else {
                    _handleRouteChange();
                }
            });
            
            // Set up nav link click handlers
            const navLinks = document.querySelectorAll('.filter-options a');
            navLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    
                    const view = this.dataset.view;
                    const filter = this.dataset.filter;
                    
                    if (view === 'dashboard') {
                        window.location.hash = 'dashboard';
                    } else if (view === 'list') {
                        if (filter === 'all') {
                            window.location.hash = 'view=list';
                        } else {
                            window.location.hash = `view=list&filter=${filter}`;
                        }
                    }
                });
            });
            
            console.log('Router initialized');
        },
        
        /**
         * Navigate to a specific route
         * @param {Object} route - Route parameters
         */
        navigate: function(route) {
            let hash = '';
            
            if (route.view === 'dashboard') {
                hash = 'dashboard';
            } else if (route.view === 'list') {
                hash = `view=list`;
                
                if (route.filter && route.filter !== 'all') {
                    hash += `&filter=${route.filter}`;
                    
                    if (route.id) {
                        hash += `&id=${encodeURIComponent(route.id)}`;
                    }
                }
                
                if (route.query) {
                    hash += `&query=${encodeURIComponent(route.query)}`;
                }
            } else if (route.view === 'detail' && route.id) {
                hash = `view=detail&id=${encodeURIComponent(route.id)}`;
            }
            
            // Update hash
            window.location.hash = hash;
        },
        
        /**
         * Navigate to category view
         * @param {string} category - The category to filter by
         */
        navigateToCategory: function(category) {
            this.navigate({
                view: 'list',
                filter: 'category',
                id: category
            });
        },
        
        /**
         * Navigate to language view
         * @param {string} language - The language to filter by
         */
        navigateToLanguage: function(language) {
            this.navigate({
                view: 'list',
                filter: 'language',
                id: language
            });
        },
        
        /**
         * Navigate to year view
         * @param {number} year - The year to filter by
         */
        navigateToYear: function(year) {
            this.navigate({
                view: 'list',
                filter: 'year',
                id: year
            });
        },
        
        /**
         * Navigate to entry detail
         * @param {string} id - The entry ID
         */
        navigateToDetail: function(id) {
            this.navigate({
                view: 'detail',
                id: id
            });
        },
        
        /**
         * Get the current route
         * @returns {Object} Current route parameters
         */
        getCurrentRoute: function() {
            return {..._currentRoute};
        }
    };
})();