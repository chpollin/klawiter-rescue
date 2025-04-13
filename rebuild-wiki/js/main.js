/**
 * main.js
 * Main application initialization
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Stefan Zweig Bibliography application...');
    
    // Initialize UI components first
    ZweigUI.initialize();
    
    // Initialize router
    ZweigRouter.initialize();
    
    // Only load data once
    if (!ZweigBibliography.isLoading() && !ZweigBibliography.isLoaded()) {
        ZweigUI.showLoading(true);
        ZweigUI.hideError();
        
        ZweigBibliography.loadData()
            .then(data => {
                console.log('Data loaded successfully:', data);
            })
            .catch(error => {
                console.error('Error in main:', error);
            });
    } else {
        console.log('Data is already being loaded or has been loaded');
    }
});