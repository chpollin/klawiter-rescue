/**
 * ui.js
 * Handles user interface interactions and displays
 */

// Verify dependencies are loaded
if (typeof ZweigTemplates === 'undefined') {
    // Create fallback implementation
    window.ZweigTemplates = {
        renderBibliographyItem: function(entry) {
            const div = document.createElement('div');
            div.className = 'bibliography-item';
            div.innerHTML = `
                <h3 class="item-title">${entry.title || 'Untitled'}</h3>
                <div class="item-meta">
                    ${entry.year ? `<span class="item-year">${parseInt(entry.year)}</span>` : ''}
                    ${entry.main_category ? `<span class="item-category">${entry.main_category}</span>` : ''}
                    ${entry.language ? `<span class="item-language">${entry.language}</span>` : ''}
                </div>
                <a href="#view=detail&id=${entry.page_id}" class="view-details">View Details</a>
            `;
            return div;
        },
        renderEntryDetail: function(entry) {
            const div = document.createElement('div');
            div.className = 'entry-detail-container';
            div.innerHTML = `
                <a href="#" class="back-to-list">&larr; Back to list</a>
                <h2>${entry.title || 'Untitled'}</h2>
                <div class="bibliographic-entry">
                    ${entry.full_bibliographic_entry || 'No details available'}
                </div>
            `;
            return div;
        },
        renderFilterControls: function() {
            return document.createElement('div');
        }
    };
}

const ZweigUI = (function() {
    // Private variables
    let _activeFilters = {
        category: null,
        year: null,
        language: null,
        timePeriod: null
    };
    let _searchQuery = '';
    
    // Cache DOM elements
    const _elements = {
        loadingIndicator: document.getElementById('loading-indicator'),
        errorMessage: document.getElementById('error-message'),
        bibliographyList: document.getElementById('bibliography-list'),
        entryDetail: document.getElementById('entry-detail'),
        filterControls: document.getElementById('filter-controls'),
        resultsCount: document.getElementById('results-count'),
        searchInput: document.getElementById('search-input'),
        searchButton: document.getElementById('search-button'),
        filterOptions: document.querySelectorAll('.filter-options a'),
        dashboardView: document.getElementById('dashboard-view'),
        totalEntries: document.getElementById('total-entries'),
        totalCategories: document.getElementById('total-categories'),
        totalLanguages: document.getElementById('total-languages'),
        yearRange: document.getElementById('year-range'),
        categoryTiles: document.getElementById('category-tiles'),
        popularLanguages: document.getElementById('popular-languages'),
        timePeriods: document.getElementById('time-periods')
    };
    
    // Private methods
    
    /**
     * Shows or hides the loading indicator
     * @param {boolean} show - Whether to show the loading indicator
     */
    const _showLoading = function(show = true) {
        if (_elements.loadingIndicator) {
            _elements.loadingIndicator.style.display = show ? 'block' : 'none';
        }
    };
    
    /**
     * Shows an error message
     * @param {string} message - The error message to display
     */
    const _showError = function(message) {
        if (_elements.errorMessage) {
            _elements.errorMessage.textContent = message;
            _elements.errorMessage.style.display = 'block';
        }
    };
    
    /**
     * Hides the error message
     */
    const _hideError = function() {
        if (_elements.errorMessage) {
            _elements.errorMessage.style.display = 'none';
        }
    };
    
    /**
     * Updates the results count display
     * @param {number} count - The number of results
     */
    const _updateResultsCount = function(count) {
        if (_elements.resultsCount) {
            _elements.resultsCount.textContent = `Found ${count} ${count === 1 ? 'entry' : 'entries'}`;
            _elements.resultsCount.style.display = 'block';
        }
    };
    
    /**
     * Hides all main content sections
     */
    const _hideAllSections = function() {
        if (_elements.dashboardView) {
            _elements.dashboardView.style.display = 'none';
        }
        if (_elements.bibliographyList) {
            _elements.bibliographyList.style.display = 'none';
        }
        if (_elements.entryDetail) {
            _elements.entryDetail.style.display = 'none';
        }
        if (_elements.resultsCount) {
            _elements.resultsCount.style.display = 'none';
        }
        if (_elements.filterControls) {
            _elements.filterControls.style.display = 'none';
        }
    };
    
    /**
     * Displays the dashboard with statistics and category tiles
     */
    const _displayDashboard = function() {
        if (!ZweigBibliography.isLoaded() || !_elements.dashboardView) {
            return;
        }
        
        // Hide other sections
        _hideAllSections();
        _hideError();
        
        // Show dashboard
        _elements.dashboardView.style.display = 'block';
        
        // Update statistics
        const allEntries = ZweigBibliography.getAllEntries();
        const categories = ZweigBibliography.getCategories();
        const languages = ZweigBibliography.getLanguages();
        const years = ZweigBibliography.getYears();
        
        // Total entries
        if (_elements.totalEntries) {
            const statNumber = _elements.totalEntries.querySelector('.stat-number');
            if (statNumber) {
                statNumber.textContent = allEntries.length;
            }
        }
        
        // Total categories
        if (_elements.totalCategories) {
            const statNumber = _elements.totalCategories.querySelector('.stat-number');
            if (statNumber) {
                statNumber.textContent = categories.length;
            }
        }
        
        // Total languages
        if (_elements.totalLanguages) {
            const statNumber = _elements.totalLanguages.querySelector('.stat-number');
            if (statNumber) {
                statNumber.textContent = languages.length;
            }
        }
        
        // Year range
        if (_elements.yearRange && years.length > 0) {
            const statText = _elements.yearRange.querySelector('.stat-text');
            if (statText) {
                const minYear = Math.min(...years);
                const maxYear = Math.max(...years);
                statText.textContent = `${minYear} - ${maxYear}`;
            }
        }
        
        // Create category tiles
        if (_elements.categoryTiles) {
            _elements.categoryTiles.innerHTML = '';
            
            // Count entries per category
            const categoryCounts = {};
            allEntries.forEach(entry => {
                if (entry.main_category) {
                    categoryCounts[entry.main_category] = (categoryCounts[entry.main_category] || 0) + 1;
                }
            });
            
            // Sort categories by count (descending)
            const sortedCategories = categories.sort((a, b) => 
                (categoryCounts[b] || 0) - (categoryCounts[a] || 0)
            );
            
            // Take top categories (limit to 12 for display)
            const topCategories = sortedCategories.slice(0, 12);
            
            // Create tiles
            topCategories.forEach(category => {
                const count = categoryCounts[category] || 0;
                const tile = document.createElement('div');
                tile.className = 'category-tile';
                tile.innerHTML = `
                    <h3 class="category-name">${category}</h3>
                    <div class="category-count">${count} ${count === 1 ? 'entry' : 'entries'}</div>
                    <a href="#view=list&filter=category&id=${encodeURIComponent(category)}" class="browse-category">Browse</a>
                `;
                _elements.categoryTiles.appendChild(tile);
            });
        }
        
        // Create language tags
        if (_elements.popularLanguages) {
            _elements.popularLanguages.innerHTML = '';
            
            // Count entries per language
            const languageCounts = {};
            allEntries.forEach(entry => {
                if (entry.language) {
                    languageCounts[entry.language] = (languageCounts[entry.language] || 0) + 1;
                }
            });
            
            // Sort languages by count (descending)
            const sortedLanguages = languages.sort((a, b) => 
                (languageCounts[b] || 0) - (languageCounts[a] || 0)
            );
            
            // Take top languages (limit to 10 for display)
            const topLanguages = sortedLanguages.slice(0, 10);
            
            // Create tags
            topLanguages.forEach(language => {
                const count = languageCounts[language] || 0;
                const tag = document.createElement('a');
                tag.className = 'filter-tag';
                tag.href = `#view=list&filter=language&id=${encodeURIComponent(language)}`;
                tag.innerHTML = `
                    <span class="tag-name">${language}</span>
                    <span class="tag-count">${count}</span>
                `;
                _elements.popularLanguages.appendChild(tag);
            });
        }
        
        // Create time period tags
        if (_elements.timePeriods) {
            _elements.timePeriods.innerHTML = '';
            
            const timePeriods = ZweigBibliography.getTimePeriods();
            
            // Count entries per time period
            const periodCounts = {};
            allEntries.forEach(entry => {
                if (entry.time_period) {
                    periodCounts[entry.time_period] = (periodCounts[entry.time_period] || 0) + 1;
                }
            });
            
            // Create tags
            timePeriods.forEach(period => {
                const count = periodCounts[period] || 0;
                if (count > 0) {
                    const tag = document.createElement('a');
                    tag.className = 'filter-tag';
                    tag.href = `#view=list&filter=timePeriod&id=${encodeURIComponent(period)}`;
                    tag.innerHTML = `
                        <span class="tag-name">${period}</span>
                        <span class="tag-count">${count}</span>
                    `;
                    _elements.timePeriods.appendChild(tag);
                }
            });
        }
    };
    
    /**
     * Displays a list of bibliography entries
     * @param {Array} entries - The bibliography entries to display
     */
    const _displayEntries = function(entries) {
        // Verify elements and data
        if (!_elements.bibliographyList || !Array.isArray(entries)) {
            return;
        }
        
        // Hide other sections
        _hideAllSections();
        _hideError();
        
        // Clear previous entries
        _elements.bibliographyList.innerHTML = '';
        
        // Update results count
        _updateResultsCount(entries.length);
        
        // Show list and count
        _elements.bibliographyList.style.display = 'grid';
        
        // No entries found
        if (entries.length === 0) {
            _elements.bibliographyList.innerHTML = '<div class="no-results">No entries found matching your criteria.</div>';
            return;
        }
        
        // Loop through entries and display them
        try {
            entries.forEach(entry => {
                const itemNode = ZweigTemplates.renderBibliographyItem(entry);
                _elements.bibliographyList.appendChild(itemNode);
            });
        } catch (err) {
            _showError('Failed to display bibliography entries');
        }
    };
    
    /**
     * Displays a detailed view of a single entry
     * @param {Object} entry - The bibliography entry to display in detail
     */
    const _displayEntryDetail = function(entry) {
        if (!entry || !_elements.entryDetail) {
            return;
        }
        
        // Hide other sections
        _hideAllSections();
        _hideError();
        
        // Clear previous content
        _elements.entryDetail.innerHTML = '';
        
        // Show detail view
        _elements.entryDetail.style.display = 'block';
        
        // Render the detail view
        try {
            const detailNode = ZweigTemplates.renderEntryDetail(entry);
            _elements.entryDetail.appendChild(detailNode);
            
            // Add back button event listener
            const backButton = _elements.entryDetail.querySelector('.back-to-list');
            if (backButton) {
                backButton.addEventListener('click', function(e) {
                    e.preventDefault();
                    window.history.back();
                });
            }
        } catch (err) {
            _showError('Failed to display entry details');
        }
    };
    
    /**
     * Initialize filter controls with available options
     */
    const _initializeFilters = function() {
        if (!ZweigBibliography.isLoaded() || !_elements.filterControls) {
            return;
        }
        
        // Get filter data
        const filterData = {
            categories: ZweigBibliography.getCategories(),
            years: ZweigBibliography.getYears(),
            languages: ZweigBibliography.getLanguages(),
            timePeriods: ZweigBibliography.getTimePeriods()
        };
        
        // Create filter controls
        try {
            const filtersElement = ZweigTemplates.renderFilterControls(filterData);
            
            // Clear previous controls
            _elements.filterControls.innerHTML = '';
            _elements.filterControls.appendChild(filtersElement);
        } catch (err) {
            // Silently fail - filters are not critical
        }
    };
    
    /**
     * Apply the current search and filters to the data
     */
    const _applyFilters = function() {
        // Get filtered results
        const filters = {};
        
        // Add active filters
        Object.keys(_activeFilters).forEach(key => {
            if (_activeFilters[key]) {
                filters[key] = _activeFilters[key];
            }
        });
        
        // Apply search and filters
        try {
            const results = ZweigBibliography.searchEntries(_searchQuery, filters);
            _displayEntries(results);
        } catch (err) {
            _showError('Failed to apply filters');
        }
    };
    
    /**
     * Set up event listeners
     */
    const _setupEventListeners = function() {
        // Search button click
        if (_elements.searchButton) {
            _elements.searchButton.addEventListener('click', function() {
                _searchQuery = _elements.searchInput.value.trim();
                
                if (_searchQuery) {
                    // Navigate to search results
                    ZweigRouter.navigate({
                        view: 'list',
                        query: _searchQuery
                    });
                }
            });
        }
        
        // Search input enter key
        if (_elements.searchInput) {
            _elements.searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    _searchQuery = _elements.searchInput.value.trim();
                    
                    if (_searchQuery) {
                        // Navigate to search results
                        ZweigRouter.navigate({
                            view: 'list',
                            query: _searchQuery
                        });
                    }
                }
            });
        }
    };
    
    // Return public methods
    return {
        /**
         * Initialize the UI
         */
        initialize: function() {
            try {
                _setupEventListeners();
                
                // Register data load handlers
                ZweigBibliography.addEventListener('loaded', function(data) {
                    _showLoading(false);
                    _hideError();
                    _initializeFilters();
                });
                
                ZweigBibliography.addEventListener('error', function(error) {
                    _showLoading(false);
                    _showError(`Failed to load bibliography data: ${error.message}`);
                });
            } catch (err) {
                // Silent fail, but UI might not work correctly
            }
        },
        
        /**
         * Display the dashboard with statistics and category tiles
         */
        displayDashboard: _displayDashboard,
        
        /**
         * Display a list of bibliography entries
         * @param {Array} entries - The bibliography entries to display
         */
        displayEntries: _displayEntries,
        
        /**
         * Display a detailed view of a single entry
         * @param {Object} entry - The bibliography entry to display in detail
         */
        displayEntryDetail: _displayEntryDetail,
        
        /**
         * Shows or hides the loading indicator
         * @param {boolean} show - Whether to show the loading indicator
         */
        showLoading: _showLoading,
        
        /**
         * Shows an error message
         * @param {string} message - The error message to display
         */
        showError: _showError,
        
        /**
         * Hides the error message
         */
        hideError: _hideError
    };
})();