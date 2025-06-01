class NotificationManager {
    constructor() {
        this.container = this.createContainer();
    }

    createContainer() {
        const container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
        return container;
    }

    show(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icon = this.getIconForType(type);
        notification.innerHTML = `
            <i class="fas ${icon}"></i>
            <span>${message}</span>
        `;
        
        this.container.appendChild(notification);
        
        // Animation d'entrée
        notification.style.animation = 'slideIn 0.3s ease-out';
        
        // Suppression automatique
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, duration);
        
        return notification;
    }

    getIconForType(type) {
        switch (type) {
            case 'success': return 'fa-check-circle';
            case 'error': return 'fa-exclamation-circle';
            case 'warning': return 'fa-exclamation-triangle';
            case 'info': return 'fa-info-circle';
            default: return 'fa-info-circle';
        }
    }

    success(message, duration = 3000) {
        return this.show(message, 'success', duration);
    }

    error(message, duration = 3000) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration = 3000) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration = 3000) {
        return this.show(message, 'info', duration);
    }
}

export const notifications = new NotificationManager();
