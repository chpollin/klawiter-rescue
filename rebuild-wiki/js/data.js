/**
 * data.js
 * Handles loading and processing the bibliography CSV data
 */

// Bibliographic data store
const ZweigBibliography = (function() {
    // Private variables
    let _data = [];
    let _isLoaded = false;
    let _isLoading = false;
    let _error = null;
    
    // Event listeners
    const _eventListeners = {
        'loaded': [],
        'error': []
    };
    
    // Private methods
    const _parseCSV = function(csvText) {
        const lines = csvText.split('\n');
        const headers = lines[0].split(',');
        
        // Check if we have valid headers
        if (!headers.includes('title') || !headers.includes('page_id')) {
            throw new Error('Invalid CSV format: Missing required headers');
        }
        
        const result = [];
        
        // Start from index 1 to skip the header row
        for (let i = 1; i < lines.length; i++) {
            // Skip empty lines
            if (!lines[i].trim()) continue;
            
            // Handle special case of commas within quoted fields
            let currentLine = lines[i];
            const values = [];
            let inQuote = false;
            let currentValue = '';
            
            for (let j = 0; j < currentLine.length; j++) {
                const char = currentLine[j];
                
                if (char === '"') {
                    inQuote = !inQuote;
                    currentValue += char;
                } else if (char === ',' && !inQuote) {
                    values.push(currentValue);
                    currentValue = '';
                } else {
                    currentValue += char;
                }
            }
            
            // Push the last value
            values.push(currentValue);
            
            // Create object with the corresponding headers
            const entry = {};
            for (let j = 0; j < headers.length; j++) {
                entry[headers[j]] = values[j] || '';
                
                // Convert year to number if possible
                if (headers[j] === 'year' && values[j]) {
                    const yearValue = parseFloat(values[j]);
                    if (!isNaN(yearValue)) {
                        entry[headers[j]] = yearValue;
                    }
                }
            }
            
            result.push(entry);
        }
        
        console.log(`Parsed ${result.length} bibliography entries`);
        return result;
    };
    
    // Return public methods
    return {
        // Load the CSV data
        loadData: async function(url = 'data/zweig_bibliography_enhanced.csv') {
            if (_isLoading) {
                console.warn('Data is already being loaded');
                return;
            }
            
            _isLoading = true;
            _error = null;
            
            try {
                console.log(`Loading bibliography data from ${url}...`);
                const response = await fetch(url);
                
                if (!response.ok) {
                    throw new Error(`HTTP error: ${response.status}`);
                }
                
                const csvText = await response.text();
                console.log(`Received ${csvText.length} bytes of data`);
                
                // Parse the CSV
                _data = _parseCSV(csvText);
                _isLoaded = true;
                _isLoading = false;
                
                // Notify listeners that data is loaded
                this.triggerEvent('loaded', { count: _data.length });
                
                return _data;
            } catch (error) {
                console.error('Failed to load bibliography data:', error);
                _error = error.message;
                _isLoading = false;
                
                // Notify listeners about the error
                this.triggerEvent('error', { message: error.message });
                
                throw error;
            }
        },
        
        // Get all data
        getAllEntries: function() {
            return [..._data]; // Return a copy to prevent direct modification
        },
        
        // Get a single entry by ID
        getEntryById: function(pageId) {
            return _data.find(entry => entry.page_id === pageId.toString());
        },
        
        // Get all available categories
        getCategories: function() {
            const categories = new Set();
            _data.forEach(entry => {
                if (entry.main_category) {
                    categories.add(entry.main_category);
                }
            });
            return Array.from(categories).sort();
        },
        
        // Get all available time periods
        getTimePeriods: function() {
            const periods = new Set();
            _data.forEach(entry => {
                if (entry.time_period) {
                    periods.add(entry.time_period);
                }
            });
            return Array.from(periods).sort();
        },
        
        // Get all available languages
        getLanguages: function() {
            const languages = new Set();
            _data.forEach(entry => {
                if (entry.language) {
                    languages.add(entry.language);
                }
            });
            return Array.from(languages).sort();
        },
        
        // Get all available years
        getYears: function() {
            const years = new Set();
            _data.forEach(entry => {
                if (entry.year) {
                    // Handle cases where year is stored as "1902.0"
                    const year = parseInt(entry.year);
                    if (!isNaN(year)) {
                        years.add(year);
                    }
                }
            });
            return Array.from(years).sort((a, b) => a - b);
        },
        
        // Search entries
        searchEntries: function(query, filters = {}) {
            if (!query && Object.keys(filters).length === 0) {
                return this.getAllEntries();
            }
            
            // Convert query to lowercase for case-insensitive search
            const lowerQuery = query ? query.toLowerCase() : '';
            
            return _data.filter(entry => {
                // Search in all text fields if query exists
                const matchesQuery = !query || [
                    entry.title,
                    entry.original_title,
                    entry.full_bibliographic_entry,
                    entry.publisher,
                    entry.location,
                    entry.clean_content
                ].some(field => field && field.toLowerCase().includes(lowerQuery));
                
                // Check all filters
                const matchesCategory = !filters.category || entry.main_category === filters.category;
                const matchesYear = !filters.year || entry.year === filters.year;
                const matchesLanguage = !filters.language || entry.language === filters.language;
                const matchesTimePeriod = !filters.timePeriod || entry.time_period === filters.timePeriod;
                
                return matchesQuery && matchesCategory && matchesYear && matchesLanguage && matchesTimePeriod;
            });
        },
        
        // Check if data is loaded
        isLoaded: function() {
            return _isLoaded;
        },
        
        // Check if data is currently loading
        isLoading: function() {
            return _isLoading;
        },
        
        // Get error message if any
        getError: function() {
            return _error;
        },
        
        // Event handling
        addEventListener: function(event, callback) {
            if (_eventListeners[event]) {
                _eventListeners[event].push(callback);
            }
        },
        
        removeEventListener: function(event, callback) {
            if (_eventListeners[event]) {
                const index = _eventListeners[event].indexOf(callback);
                if (index !== -1) {
                    _eventListeners[event].splice(index, 1);
                }
            }
        },
        
        triggerEvent: function(event, data) {
            if (_eventListeners[event]) {
                _eventListeners[event].forEach(callback => {
                    callback(data);
                });
            }
        }
    };
})();