/**
 * Module pour surveiller les performances et détecter les problèmes potentiels
 */
import { errorLogger } from './errorLogger.js';

class PerformanceMonitor {
    constructor() {
        this.longTaskThreshold = 200; // ms
        this.networkRequestThreshold = 5000; // ms
        this.initObservers();
        console.log('PerformanceMonitor: Initialized');
    }
    
    /**
     * Initialise les observateurs de performance
     */
    initObservers() {
        // Observer pour les tâches longues
        if ('PerformanceObserver' in window) {
            try {
                // Observer pour les tâches longues (bloquant le thread principal)
                const longTaskObserver = new PerformanceObserver(this.handleLongTasks.bind(this));
                longTaskObserver.observe({ entryTypes: ['longtask'] });
                
                // Observer pour les requêtes réseau
                const resourceObserver = new PerformanceObserver(this.handleResourceTiming.bind(this));
                resourceObserver.observe({ entryTypes: ['resource'] });
                
                console.log('PerformanceObserver: Registered successfully');
            } catch (e) {
                console.warn('PerformanceObserver not fully supported:', e);
            }
        }
        
        // Surveiller les requêtes fetch
        this.monitorFetch();
    }
    
    /**
     * Gère les notifications de tâches longues
     */
    handleLongTasks(entries) {
        entries.getEntries().forEach(entry => {
            if (entry.duration > this.longTaskThreshold) {
                errorLogger.logError({
                    type: 'LONG_TASK',
                    message: `Long task detected: ${Math.round(entry.duration)}ms`,
                    component: 'Performance',
                    stack: `Attribution: ${JSON.stringify(entry.attribution)}`
                });
            }
        });
    }
    
    /**
     * Gère les métriques de timing des ressources
     */
    handleResourceTiming(entries) {
        entries.getEntries().forEach(entry => {
            // Ignorer les requêtes de polling
            if (entry.name.includes('/status/') || entry.name.includes('/api/get_auto_mode_status')) {
                return;
            }
            
            const duration = entry.duration;
            if (duration > this.networkRequestThreshold) {
                errorLogger.logError({
                    type: 'SLOW_NETWORK',
                    message: `Slow network request: ${Math.round(duration)}ms for ${entry.name}`,
                    component: 'Network',
                    stack: `Initiator: ${entry.initiatorType}, Start: ${new Date(entry.startTime).toISOString()}`
                });
            }
        });
    }
    
    /**
     * Surveille les requêtes fetch pour détecter les erreurs
     */
    monitorFetch() {
        const originalFetch = window.fetch;
        
        window.fetch = async (...args) => {
            const url = args[0] instanceof Request ? args[0].url : args[0];
            
            // Ignorer les requêtes de polling
            if (url.includes('/status/') || url.includes('/api/get_auto_mode_status')) {
                return originalFetch.apply(window, args);
            }
            
            const startTime = performance.now();
            try {
                const response = await originalFetch.apply(window, args);
                
                const duration = performance.now() - startTime;
                if (duration > this.networkRequestThreshold) {
                    errorLogger.logError({
                        type: 'SLOW_FETCH',
                        message: `Slow fetch request: ${Math.round(duration)}ms for ${url}`,
                        component: 'Network',
                        stack: `Method: ${args[1]?.method || 'GET'}, Start: ${new Date().toISOString()}`
                    });
                }
                
                if (!response.ok) {
                    errorLogger.logError({
                        type: 'FETCH_ERROR',
                        message: `Fetch error: ${response.status} ${response.statusText} for ${url}`,
                        component: 'Network',
                        stack: `Method: ${args[1]?.method || 'GET'}, Status: ${response.status}`
                    });
                }
                
                return response;
            } catch (error) {
                errorLogger.logError({
                    type: 'FETCH_EXCEPTION',
                    message: `Fetch exception: ${error.message} for ${url}`,
                    component: 'Network',
                    stack: error.stack || 'No stack trace available'
                });
                throw error;
            }
        };
    }
    
    /**
     * Surveille un élément DOM spécifique pour détecter les problèmes de rendu
     */
    monitorElement(elementId, checkInterval = 5000) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.warn(`Element with ID '${elementId}' not found for monitoring`);
            return;
        }
        
        let lastRenderTime = Date.now();
        let checkIntervalId = setInterval(() => {
            const now = Date.now();
            if (now - lastRenderTime > checkInterval * 2) {
                errorLogger.logError({
                    type: 'RENDER_STALL',
                    message: `Element '${elementId}' hasn't updated in ${Math.round((now - lastRenderTime) / 1000)}s`,
                    component: 'UI',
                    stack: `Element: ${elementId}, Last render: ${new Date(lastRenderTime).toISOString()}`
                });
            }
        }, checkInterval);
        
        // Observer les mutations de l'élément
        const observer = new MutationObserver(() => {
            lastRenderTime = Date.now();
        });
        
        observer.observe(element, {
            childList: true,
            attributes: true,
            characterData: true,
            subtree: true
        });
        
        return {
            stop: () => {
                clearInterval(checkIntervalId);
                observer.disconnect();
            }
        };
    }
}

// Exporter une instance unique
export const performanceMonitor = new PerformanceMonitor();
