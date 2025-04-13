/**
 * templates.js
 * Handles HTML rendering templates
 */

const ZweigTemplates = (function() {
    /**
     * Create a bibliography item HTML element
     * @param {Object} entry - The bibliography entry data
     * @returns {HTMLElement} The rendered HTML element
     */
    const _renderBibliographyItem = function(entry) {
        if (!entry) {
            return null;
        }
        
        // Clone the template
        const template = document.getElementById('bibliography-item-template');
        if (!template) {
            console.error('Bibliography item template not found');
            return document.createElement('div');
        }
        
        const clone = template.content.cloneNode(true);
        
        // Fill in the data
        // Title
        const titleEl = clone.querySelector('.item-title');
        if (titleEl) {
            titleEl.textContent = entry.title || 'Untitled';
        }
        
        // Year
        const yearEl = clone.querySelector('.item-year');
        if (yearEl && entry.year) {
            yearEl.textContent = entry.year;
        } else if (yearEl) {
            yearEl.style.display = 'none';
        }
        
        // Category
        const categoryEl = clone.querySelector('.item-category');
        if (categoryEl && entry.main_category) {
            categoryEl.textContent = entry.main_category;
        } else if (categoryEl) {
            categoryEl.style.display = 'none';
        }
        
        // Language
        const languageEl = clone.querySelector('.item-language');
        if (languageEl && entry.language) {
            languageEl.textContent = entry.language;
        } else if (languageEl) {
            languageEl.style.display = 'none';
        }
        
        // Details link
        const detailsLink = clone.querySelector('.view-details');
        if (detailsLink && entry.page_id) {
            detailsLink.href = `#view=${entry.page_id}`;
        }
        
        return clone;
    };
    
    /**
     * Create an entry detail HTML element
     * @param {Object} entry - The bibliography entry data
     * @returns {HTMLElement} The rendered HTML element
     */
    const _renderEntryDetail = function(entry) {
        if (!entry) {
            return null;
        }
        
        // Clone the template
        const template = document.getElementById('entry-detail-template');
        if (!template) {
            console.error('Entry detail template not found');
            return document.createElement('div');
        }
        
        const clone = template.content.cloneNode(true);
        
        // Fill in the data
        // Title
        const titleEl = clone.querySelector('.detail-title');
        if (titleEl) {
            titleEl.textContent = entry.title || 'Untitled';
        }
        
        // Original title
        const originalTitleEl = clone.querySelector('.original-title');
        if (originalTitleEl) {
            originalTitleEl.textContent = entry.original_title || '-';
        }
        
        // Year
        const yearEl = clone.querySelector('.year');
        if (yearEl) {
            yearEl.textContent = entry.year || '-';
        }
        
        // Publisher
        const publisherEl = clone.querySelector('.publisher');
        if (publisherEl) {
            publisherEl.textContent = entry.publisher || '-';
        }
        
        // Location
        const locationEl = clone.querySelector('.location');
        if (locationEl) {
            locationEl.textContent = entry.location || '-';
        }
        
        // Language
        const languageEl = clone.querySelector('.language');
        if (languageEl) {
            languageEl.textContent = entry.language || '-';
        }
        
        // Categories
        const categoriesEl = clone.querySelector('.categories');
        if (categoriesEl) {
            categoriesEl.textContent = entry.main_category || '-';
        }
        
        // Time period
        const timePeriodEl = clone.querySelector('.time-period');
        if (timePeriodEl) {
            timePeriodEl.textContent = entry.time_period || '-';
        }
        
        // Full bibliographic entry
        const entryContentEl = clone.querySelector('.entry-content');
        if (entryContentEl) {
            entryContentEl.textContent = entry.full_bibliographic_entry || 'No bibliographic entry available';
        }
        
        // Back link
        const backLink = clone.querySelector('.back-to-list');
        if (backLink) {
            backLink.href = '#';
        }
        
        return clone;
    };
    
    /**
     * Create filter controls HTML element
     * @param {Object} filterData - The filter data (categories, years, etc.)
     * @returns {HTMLElement} The rendered HTML element
     */
    const _renderFilterControls = function(filterData) {
        if (!filterData) {
            return null;
        }
        
        const container = document.createElement('div');
        container.className = 'filter-controls-container';
        
        // Categories filter
        if (filterData.categories && filterData.categories.length > 0) {
            const categoryFilter = document.createElement('div');
            categoryFilter.className = 'filter-group';
            categoryFilter.innerHTML = `
                <h3>Categories</h3>
                <div class="filter-options-container category-options"></div>
            `;
            
            const optionsContainer = categoryFilter.querySelector('.category-options');
            
            filterData.categories.forEach(category => {
                const option = document.createElement('div');
                option.className = 'filter-option';
                option.innerHTML = `
                    <label>
                        <input type="radio" name="category-filter" value="${category}">
                        ${category}
                    </label>
                `;
                
                optionsContainer.appendChild(option);
            });
            
            // Add event listeners
            categoryFilter.querySelectorAll('input[type="radio"]').forEach(input => {
                input.addEventListener('change', function() {
                    const categoryValue = this.value;
                    const isSelected = this.checked;
                    
                    // Dispatch a custom event
                    document.dispatchEvent(new CustomEvent('filter-changed', {
                        detail: {
                            type: 'category',
                            value: categoryValue,
                            selected: isSelected
                        }
                    }));
                });
            });
            
            container.appendChild(categoryFilter);
        }
        
        // Languages filter
        if (filterData.languages && filterData.languages.length > 0) {
            const languageFilter = document.createElement('div');
            languageFilter.className = 'filter-group';
            languageFilter.innerHTML = `
                <h3>Languages</h3>
                <div class="filter-options-container language-options"></div>
            `;
            
            const optionsContainer = languageFilter.querySelector('.language-options');
            
            filterData.languages.forEach(language => {
                const option = document.createElement('div');
                option.className = 'filter-option';
                option.innerHTML = `
                    <label>
                        <input type="radio" name="language-filter" value="${language}">
                        ${language}
                    </label>
                `;
                
                optionsContainer.appendChild(option);
            });
            
            // Add event listeners
            languageFilter.querySelectorAll('input[type="radio"]').forEach(input => {
                input.addEventListener('change', function() {
                    const languageValue = this.value;
                    const isSelected = this.checked;
                    
                    // Dispatch a custom event
                    document.dispatchEvent(new CustomEvent('filter-changed', {
                        detail: {
                            type: 'language',
                            value: languageValue,
                            selected: isSelected
                        }
                    }));
                });
            });
            
            container.appendChild(languageFilter);
        }
        
        // Years filter
        if (filterData.years && filterData.years.length > 0) {
            const yearFilter = document.createElement('div');
            yearFilter.className = 'filter-group';
            yearFilter.innerHTML = `
                <h3>Years</h3>
                <div class="filter-options-container year-options"></div>
            `;
            
            const optionsContainer = yearFilter.querySelector('.year-options');
            
            filterData.years.forEach(year => {
                const option = document.createElement('div');
                option.className = 'filter-option';
                option.innerHTML = `
                    <label>
                        <input type="radio" name="year-filter" value="${year}">
                        ${year}
                    </label>
                `;
                
                optionsContainer.appendChild(option);
            });
            
            // Add event listeners
            yearFilter.querySelectorAll('input[type="radio"]').forEach(input => {
                input.addEventListener('change', function() {
                    const yearValue = parseInt(this.value);
                    const isSelected = this.checked;
                    
                    // Dispatch a custom event
                    document.dispatchEvent(new CustomEvent('filter-changed', {
                        detail: {
                            type: 'year',
                            value: yearValue,
                            selected: isSelected
                        }
                    }));
                });
            });
            
            container.appendChild(yearFilter);
        }
        
        // Time periods filter
        if (filterData.timePeriods && filterData.timePeriods.length > 0) {
            const timePeriodFilter = document.createElement('div');
            timePeriodFilter.className = 'filter-group';
            timePeriodFilter.innerHTML = `
                <h3>Time Periods</h3>
                <div class="filter-options-container time-period-options"></div>
            `;
            
            const optionsContainer = timePeriodFilter.querySelector('.time-period-options');
            
            filterData.timePeriods.forEach(period => {
                const option = document.createElement('div');
                option.className = 'filter-option';
                option.innerHTML = `
                    <label>
                        <input type="radio" name="time-period-filter" value="${period}">
                        ${period}
                    </label>
                `;
                
                optionsContainer.appendChild(option);
            });
            
            // Add event listeners
            timePeriodFilter.querySelectorAll('input[type="radio"]').forEach(input => {
                input.addEventListener('change', function() {
                    const periodValue = this.value;
                    const isSelected = this.checked;
                    
                    // Dispatch a custom event
                    document.dispatchEvent(new CustomEvent('filter-changed', {
                        detail: {
                            type: 'timePeriod',
                            value: periodValue,
                            selected: isSelected
                        }
                    }));
                });
            });
            
            container.appendChild(timePeriodFilter);
        }
        
        return container;
    };
    
    // Return public methods
    return {
        renderBibliographyItem: _renderBibliographyItem,
        renderEntryDetail: _renderEntryDetail,
        renderFilterControls: _renderFilterControls
    };
})();