import { animations } from './animations.js';
import { setUserManuallyClosedActiveLogPanel } from './state.js';

class ActiveLogPanel {
    constructor() {
        this.panel = this.createPanel();
        this.currentStepKey = null;
        this.isVisible = false;
        this.currentSpecificLogIndex = null;
    }

    createPanel() {
        const panel = document.createElement('div');
        panel.className = 'active-log-panel';
        panel.innerHTML = `
            <div class="active-log-header">
                <h3>Logs de l'étape en cours</h3>
                <div class="log-tabs">
                    <button class="log-tab active" data-tab="main">Logs Principaux</button>
                    <button class="log-tab" data-tab="specific">Logs Spécifiques</button>
                </div>
                <div class="active-log-controls">
                    <button class="minimize-button" title="Réduire/Agrandir">
                        <i class="fas fa-chevron-down"></i>
                    </button>
                    <button class="close-button" title="Fermer">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            <div class="active-log-content">
                <div class="log-main visible"></div>
                <div class="log-specific">
                    <div class="specific-log-nav">
                        <select class="specific-log-select"></select>
                    </div>
                    <div class="specific-log-content"></div>
                </div>
            </div>
        `;

        // Gestionnaire pour les onglets
        const tabs = panel.querySelectorAll('.log-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Gestionnaire pour la sélection des logs spécifiques
        const logSelect = panel.querySelector('.specific-log-select');
        logSelect.addEventListener('change', (e) => {
            this.loadSpecificLog(parseInt(e.target.value));
        });

        // Gestionnaire pour le bouton minimize
        panel.querySelector('.minimize-button').addEventListener('click', () => {
            this.toggleMinimize();
        });

        // Gestionnaire pour le bouton close
        panel.querySelector('.close-button').addEventListener('click', () => {
            this.hide(true);
        });

        document.body.appendChild(panel);
        panel.style.display = 'none';
        return panel;
    }

    async show(stepKey, stepName, specificLogs = []) {
        this.currentStepKey = stepKey;
        
        // Mettre à jour le titre
        this.panel.querySelector('h3').textContent = `Logs - ${stepName}`;
        
        // Mettre à jour la liste des logs spécifiques
        const logSelect = this.panel.querySelector('.specific-log-select');
        logSelect.innerHTML = '';
        specificLogs.forEach((log, index) => {
            const option = document.createElement('option');
            option.value = index;
            option.textContent = log.name || `Log ${index + 1}`;
            logSelect.appendChild(option);
        });
        
        // Activer/désactiver l'onglet des logs spécifiques
        const specificTab = this.panel.querySelector('.log-tab[data-tab="specific"]');
        if (specificLogs.length > 0) {
            specificTab.removeAttribute('disabled');
            // Charger le premier log spécifique
            if (this.currentSpecificLogIndex === null) {
                this.loadSpecificLog(0);
            }
        } else {
            specificTab.setAttribute('disabled', 'true');
            this.switchTab('main');
        }
        
        // Repositionner les autres éléments
        document.querySelector('.steps-container').classList.add('with-active-log');
        
        if (!this.isVisible) {
            this.panel.style.display = 'block';
            await animations.slideDown(this.panel);
            this.isVisible = true;
        }
    }

    switchTab(tabName) {
        const tabs = this.panel.querySelectorAll('.log-tab');
        const mainContent = this.panel.querySelector('.log-main');
        const specificContent = this.panel.querySelector('.log-specific');
        
        tabs.forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
        
        if (tabName === 'main') {
            mainContent.classList.add('visible');
            specificContent.classList.remove('visible');
        } else {
            mainContent.classList.remove('visible');
            specificContent.classList.add('visible');
        }
    }

    async loadSpecificLog(logIndex) {
        this.currentSpecificLogIndex = logIndex;
        const content = this.panel.querySelector('.specific-log-content');
        content.innerHTML = '<div class="loading">Chargement...</div>';

        try {
            const response = await fetch(`/get_specific_log/${this.currentStepKey}/${logIndex}`);
            const data = await response.json();

            if (data.error) {
                content.innerHTML = `<div class="error-message">${data.error}</div>`;
                return;
            }

            if (!data.content) {
                content.innerHTML = '<div class="empty-message">Aucun contenu disponible</div>';
                return;
            }

            content.innerHTML = `
                <div class="log-path">${data.path}</div>
                <div class="log-content">${data.content}</div>
            `;

        } catch (error) {
            content.innerHTML = `<div class="error-message">Erreur lors du chargement du log: ${error}</div>`;
        }
    }

    updateMainLog(logContent) {
        const mainLog = this.panel.querySelector('.log-main');
        mainLog.innerHTML = logContent;
        mainLog.scrollTop = mainLog.scrollHeight;
    }

    async hide(userInitiated = false) {
        if (this.isVisible) {
            await animations.slideUp(this.panel);
            this.panel.style.display = 'none';
            this.isVisible = false;
            this.currentStepKey = null;
            this.currentSpecificLogIndex = null;
            
            if (userInitiated) {
                setUserManuallyClosedActiveLogPanel(true);
            }
            
            document.querySelector('.steps-container').classList.remove('with-active-log');
        }
    }

    async toggleMinimize() {
        const content = this.panel.querySelector('.active-log-content');
        const button = this.panel.querySelector('.minimize-button i');
        
        if (content.style.display !== 'none') {
            await animations.slideUp(content);
            button.className = 'fas fa-chevron-up';
            this.panel.classList.add('minimized');
        } else {
            content.style.display = 'block';
            await animations.slideDown(content);
            button.className = 'fas fa-chevron-down';
            this.panel.classList.remove('minimized');
        }
    }

    isActiveStep(stepKey) {
        return this.currentStepKey === stepKey && this.isVisible;
    }

    getElement() {
        return this.panel;
    }
}

export const activeLogPanel = new ActiveLogPanel();
