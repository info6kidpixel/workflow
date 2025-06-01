import { PROCESS_INFO_CLIENT, getIsAnySequenceRunning, getAutoModeEnabled, getUserManuallyClosedActiveLogPanel } from './state.js';

/**
 * Outils de débogage pour l'application
 * Ce module fournit des fonctionnalités pour aider au débogage de l'application
 */

class DebugTools {
    constructor() {
        this.isDebugMode = false;
        this.logHistory = [];
        this.maxLogHistory = 100;
        this.debugPanel = null;

        // Intercepter console.log, console.error, etc.
        this.setupConsoleInterception();

        // Ajouter un raccourci clavier pour afficher/masquer le panneau de débogage
        document.addEventListener('keydown', (event) => {
            // Ctrl+Shift+D pour afficher/masquer le panneau de débogage
            if (event.ctrlKey && event.shiftKey && event.key === 'D') {
                event.preventDefault();
                this.toggleDebugPanel();
            }
        });

        console.log('DebugTools: Initialized');
    }

    /**
     * Configure l'interception des méthodes de la console
     */
    setupConsoleInterception() {
        const originalConsole = {
            log: console.log,
            warn: console.warn,
            error: console.error,
            info: console.info,
            debug: console.debug
        };

        // Intercepter les méthodes de la console
        Object.keys(originalConsole).forEach(method => {
            console[method] = (...args) => {
                // Appeler la méthode originale
                originalConsole[method].apply(console, args);

                // Ajouter au journal
                this.addToLogHistory({
                    type: method.toUpperCase(),
                    message: args.map(arg => this.formatLogArgument(arg)).join(' '),
                    timestamp: new Date()
                });

                // Mettre à jour le panneau de débogage s'il est visible
                if (this.debugPanel && this.isDebugMode) {
                    this.updateDebugPanel();
                }
            };
        });
    }

    /**
     * Formate un argument de log pour l'affichage
     */
    formatLogArgument(arg) {
        if (arg === null) return 'null';
        if (arg === undefined) return 'undefined';
        if (typeof arg === 'object') {
            try {
                return JSON.stringify(arg);
            } catch (e) {
                return String(arg);
            }
        }
        return String(arg);
    }

    /**
     * Ajoute une entrée au journal
     */
    addToLogHistory(entry) {
        this.logHistory.push(entry);
        if (this.logHistory.length > this.maxLogHistory) {
            this.logHistory.shift();
        }
    }

    /**
     * Affiche ou masque le panneau de débogage
     */
    toggleDebugPanel() {
        this.isDebugMode = !this.isDebugMode;

        if (this.isDebugMode) {
            this.showDebugPanel();
        } else if (this.debugPanel) {
            this.debugPanel.remove();
            this.debugPanel = null;
        }
    }

    /**
     * Affiche le panneau de débogage
     */
    showDebugPanel() {
        if (!this.debugPanel) {
            this.debugPanel = document.createElement('div');
            this.debugPanel.className = 'debug-panel';
            this.debugPanel.innerHTML = `
                <div class="debug-header">
                    <h3>Panneau de Débogage</h3>
                    <div class="debug-controls">
                        <button id="debug-clear">Effacer</button>
                        <button id="debug-close">Fermer</button>
                    </div>
                </div>
                <div class="debug-content">
                    <div class="debug-tabs">
                        <button class="debug-tab active" data-tab="logs">Logs</button>
                        <button class="debug-tab" data-tab="state">État</button>
                        <button class="debug-tab" data-tab="network">Réseau</button>
                    </div>
                    <div class="debug-tab-content active" id="debug-logs"></div>
                    <div class="debug-tab-content" id="debug-state"></div>
                    <div class="debug-tab-content" id="debug-network"></div>
                </div>
            `;

            // Ajouter les styles
            const style = document.createElement('style');
            style.textContent = `
                .debug-panel {
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    width: 100%;
                    height: 300px;
                    background-color: rgba(0, 0, 0, 0.9);
                    color: #fff;
                    z-index: 9999;
                    font-family: monospace;
                    display: flex;
                    flex-direction: column;
                    border-top: 1px solid #444;
                }
                .debug-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 5px 10px;
                    background-color: #333;
                    border-bottom: 1px solid #444;
                }
                .debug-header h3 {
                    margin: 0;
                    font-size: 14px;
                }
                .debug-controls {
                    display: flex;
                    gap: 5px;
                }
                .debug-controls button {
                    background-color: #555;
                    border: none;
                    color: #fff;
                    padding: 3px 8px;
                    cursor: pointer;
                    font-size: 12px;
                }
                .debug-controls button:hover {
                    background-color: #666;
                }
                .debug-content {
                    flex: 1;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                }
                .debug-tabs {
                    display: flex;
                    background-color: #222;
                    border-bottom: 1px solid #444;
                }
                .debug-tab {
                    background-color: transparent;
                    border: none;
                    color: #aaa;
                    padding: 5px 10px;
                    cursor: pointer;
                    font-size: 12px;
                }
                .debug-tab.active {
                    color: #fff;
                    background-color: #333;
                    border-bottom: 2px solid #0af;
                }
                .debug-tab-content {
                    display: none;
                    flex: 1;
                    overflow-y: auto;
                    padding: 10px;
                    font-size: 12px;
                }
                .debug-tab-content.active {
                    display: block;
                }
                .log-entry {
                    margin-bottom: 5px;
                    border-bottom: 1px solid #333;
                    padding-bottom: 3px;
                }
                .log-timestamp {
                    color: #888;
                    margin-right: 5px;
                }
                .log-type {
                    display: inline-block;
                    min-width: 60px;
                    padding: 1px 5px;
                    border-radius: 3px;
                    margin-right: 5px;
                    text-align: center;
                }
                .log-type-LOG {
                    background-color: #333;
                    color: #fff;
                }
                .log-type-INFO {
                    background-color: #0066cc;
                    color: #fff;
                }
                .log-type-WARN {
                    background-color: #cc9900;
                    color: #000;
                }
                .log-type-ERROR {
                    background-color: #cc0000;
                    color: #fff;
                }
                .log-type-DEBUG {
                    background-color: #009900;
                    color: #fff;
                }
                .log-message {
                    color: #ddd;
                    word-break: break-word;
                }
            `;

            document.head.appendChild(style);
            document.body.appendChild(this.debugPanel);

            // Ajouter les gestionnaires d'événements
            document.getElementById('debug-clear').addEventListener('click', () => {
                this.logHistory = [];
                this.updateDebugPanel();
            });

            document.getElementById('debug-close').addEventListener('click', () => {
                this.toggleDebugPanel();
            });

            // Gestionnaires pour les onglets
            document.querySelectorAll('.debug-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.debug-tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.debug-tab-content').forEach(c => c.classList.remove('active'));

                    tab.classList.add('active');
                    document.getElementById(`debug-${tab.dataset.tab}`).classList.add('active');

                    // Mettre à jour le contenu de l'onglet actif
                    this.updateActiveTabContent(tab.dataset.tab);
                });
            });
        }

        this.updateDebugPanel();
    }

    /**
     * Met à jour le contenu du panneau de débogage
     */
    updateDebugPanel() {
        if (!this.debugPanel) return;

        // Mettre à jour l'onglet actif
        const activeTab = this.debugPanel.querySelector('.debug-tab.active');
        if (activeTab) {
            this.updateActiveTabContent(activeTab.dataset.tab);
        }
    }

    /**
     * Met à jour le contenu de l'onglet actif
     */
    updateActiveTabContent(tabName) {
        switch (tabName) {
            case 'logs':
                this.updateLogsTab();
                break;
            case 'state':
                this.updateStateTab();
                break;
            case 'network':
                this.updateNetworkTab();
                break;
        }
    }

    /**
     * Met à jour l'onglet des logs
     */
    updateLogsTab() {
        const logsContainer = document.getElementById('debug-logs');
        if (!logsContainer) return;

        logsContainer.innerHTML = this.logHistory.map(entry => `
            <div class="log-entry">
                <span class="log-timestamp">${entry.timestamp.toLocaleTimeString()}</span>
                <span class="log-type log-type-${entry.type}">${entry.type}</span>
                <span class="log-message">${entry.message}</span>
            </div>
        `).join('');

        // Faire défiler vers le bas
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }

    /**
     * Met à jour l'onglet d'état
     */
    updateStateTab() {
        const stateContainer = document.getElementById('debug-state');
        if (!stateContainer) return;

        const appState = {
            PROCESS_INFO_CLIENT: PROCESS_INFO_CLIENT, // Utiliser l'import
            isAnySequenceRunning: getIsAnySequenceRunning(), // Utiliser l'import
            autoModeEnabled: getAutoModeEnabled(), // Utiliser l'import
            userManuallyClosedActiveLogPanel: getUserManuallyClosedActiveLogPanel() // Utiliser l'import
        };

        stateContainer.innerHTML = `
            <h4>État de l'Application</h4>
            <pre>${JSON.stringify(appState, null, 2)}</pre>
        `;
    }

    /**
     * Met à jour l'onglet réseau
     */
    updateNetworkTab() {
        const networkContainer = document.getElementById('debug-network');
        if (!networkContainer) return;

        // Récupérer les performances réseau
        const resources = performance.getEntriesByType('resource');
        const networkStats = resources.map(entry => ({
            name: entry.name,
            duration: Math.round(entry.duration),
            size: entry.transferSize || 'N/A',
            type: entry.initiatorType
        })).sort((a, b) => b.duration - a.duration);

        networkContainer.innerHTML = `
            <h4>Requêtes Réseau (${networkStats.length})</h4>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <th style="text-align: left; padding: 5px; border-bottom: 1px solid #444;">URL</th>
                    <th style="text-align: right; padding: 5px; border-bottom: 1px solid #444;">Durée (ms)</th>
                    <th style="text-align: right; padding: 5px; border-bottom: 1px solid #444;">Taille (o)</th>
                    <th style="text-align: left; padding: 5px; border-bottom: 1px solid #444;">Type</th>
                </tr>
                ${networkStats.map(stat => `
                    <tr>
                        <td style="text-align: left; padding: 5px; border-bottom: 1px solid #333;">${stat.name}</td>
                        <td style="text-align: right; padding: 5px; border-bottom: 1px solid #333;">${stat.duration}</td>
                        <td style="text-align: right; padding: 5px; border-bottom: 1px solid #333;">${stat.size}</td>
                        <td style="text-align: left; padding: 5px; border-bottom: 1px solid #333;">${stat.type}</td>
                    </tr>
                `).join('')}
            </table>
        `;
    }
}

// Exporter une instance unique
export const debugTools = new DebugTools();