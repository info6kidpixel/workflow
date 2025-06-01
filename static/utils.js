// Formatage de la durée
export function formatDuration(seconds) {
    if (!seconds || seconds < 0) return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    let timeString = '';
    if (hours > 0) timeString += `${hours}h `;
    if (minutes > 0 || hours > 0) timeString += `${minutes}m `;
    timeString += `${remainingSeconds}s`;
    
    return timeString.trim();
}

// Échappement HTML
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Formatage de la date
export function formatDate(date) {
    if (!(date instanceof Date)) {
        date = new Date(date);
    }
    return date.toLocaleString('fr-FR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Génération d'un ID unique
export function generateUniqueId(prefix = '') {
    return `${prefix}${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Debounce pour limiter les appels fréquents
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle pour limiter la fréquence des appels
export function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func(...args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Vérification si un élément est visible dans le viewport
export function isElementInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// Copie sécurisée d'un objet
export function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj);
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (obj instanceof Object) {
        return Object.fromEntries(
            Object.entries(obj).map(([key, value]) => [key, deepClone(value)])
        );
    }
    return obj;
}

// Formatage des nombres avec séparateurs de milliers
export function formatNumber(number) {
    return new Intl.NumberFormat('fr-FR').format(number);
}

// Validation d'une adresse email
export function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

// Conversion de taille de fichier en format lisible
export function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Extraction des paramètres d'URL
export function getUrlParameters() {
    const params = new URLSearchParams(window.location.search);
    return Object.fromEntries(params.entries());
}

// Vérification de support des fonctionnalités du navigateur
export const browserSupport = {
    localStorage: !!window.localStorage,
    webWorkers: !!window.Worker,
    webGL: (() => {
        try {
            return !!window.WebGLRenderingContext && 
                   !!document.createElement('canvas').getContext('experimental-webgl');
        } catch(e) {
            return false;
        }
    })(),
    touchEvents: ('ontouchstart' in window)
};
