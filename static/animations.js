export const animations = {
    async fadeIn(element, duration = 300) {
        if (!element) return;
        element.style.display = 'block';
        element.style.opacity = '0';
        
        // Force a reflow to ensure the display:block has taken effect
        element.offsetHeight;
        
        element.style.transition = `opacity ${duration}ms ease-in-out`;
        element.style.opacity = '1';
        
        return new Promise(resolve => {
            setTimeout(() => {
                element.style.transition = '';
                resolve();
            }, duration);
        });
    },

    async fadeOut(element, duration = 300) {
        if (!element) return;
        element.style.transition = `opacity ${duration}ms ease-in-out`;
        element.style.opacity = '0';
        
        return new Promise(resolve => {
            setTimeout(() => {
                element.style.display = 'none';
                element.style.transition = '';
                element.style.opacity = '';
                resolve();
            }, duration);
        });
    },

    async slideDown(element, duration = 300) {
        if (!element) return;
        element.style.display = 'block';
        const height = element.scrollHeight;
        element.style.overflow = 'hidden';
        element.style.height = '0';
        element.style.paddingTop = '0';
        element.style.paddingBottom = '0';
        element.style.marginTop = '0';
        element.style.marginBottom = '0';
        
        // Force a reflow
        element.offsetHeight;
        
        element.style.transition = `all ${duration}ms ease-in-out`;
        element.style.height = `${height}px`;
        element.style.paddingTop = '';
        element.style.paddingBottom = '';
        element.style.marginTop = '';
        element.style.marginBottom = '';
        
        return new Promise(resolve => {
            setTimeout(() => {
                element.style.height = '';
                element.style.overflow = '';
                element.style.transition = '';
                resolve();
            }, duration);
        });
    },

    async slideUp(element, duration = 300) {
        if (!element) return;
        element.style.overflow = 'hidden';
        element.style.height = `${element.scrollHeight}px`;
        
        // Force a reflow
        element.offsetHeight;
        
        element.style.transition = `all ${duration}ms ease-in-out`;
        element.style.height = '0';
        element.style.paddingTop = '0';
        element.style.paddingBottom = '0';
        element.style.marginTop = '0';
        element.style.marginBottom = '0';
        
        return new Promise(resolve => {
            setTimeout(() => {
                element.style.display = 'none';
                element.style.height = '';
                element.style.overflow = '';
                element.style.transition = '';
                element.style.paddingTop = '';
                element.style.paddingBottom = '';
                element.style.marginTop = '';
                element.style.marginBottom = '';
                resolve();
            }, duration);
        });
    },

    pulse(element, duration = 600) {
        if (!element) return;
        element.style.transition = `transform ${duration}ms ease-in-out`;
        element.style.transform = 'scale(1.02)';
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
            setTimeout(() => {
                element.style.transition = '';
            }, duration);
        }, duration / 2);
    },

    shake(element, duration = 600) {
        if (!element) return;
        element.style.animation = `shake ${duration}ms ease-in-out`;
        setTimeout(() => {
            element.style.animation = '';
        }, duration);
    },

    highlight(element, duration = 1000) {
        if (!element) return;
        const originalBackground = element.style.backgroundColor;
        element.style.transition = `background-color ${duration}ms ease-in-out`;
        element.style.backgroundColor = 'var(--highlight-color, rgba(62, 151, 255, 0.2))';
        
        setTimeout(() => {
            element.style.backgroundColor = originalBackground;
            setTimeout(() => {
                element.style.transition = '';
            }, duration);
        }, duration);
    },

    success(element, duration = 1000) {
        if (!element) return;
        const originalBackground = element.style.backgroundColor;
        element.style.transition = `background-color ${duration}ms ease-in-out`;
        element.style.backgroundColor = 'var(--success-soft)';
        
        setTimeout(() => {
            element.style.backgroundColor = originalBackground;
            setTimeout(() => {
                element.style.transition = '';
            }, duration);
        }, duration);
    },

    async fadeText(element, newText, duration = 300) {
        if (!element) return;
        await this.fadeOut(element, duration / 2);
        element.textContent = newText;
        await this.fadeIn(element, duration / 2);
    },

    bounce(element, duration = 1000) {
        if (!element) return;
        element.style.animation = `bounce ${duration}ms cubic-bezier(0.36, 0, 0.66, -0.56)`;
        setTimeout(() => {
            element.style.animation = '';
        }, duration);
    }
};
