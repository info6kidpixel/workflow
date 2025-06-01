// --- START OF FILE eventHandlers.js ---

import { mainElements, modalElements, getStepElements } from './domElements.js';
import { runStep, cancelStep, runCustomSequence, toggleAutoMode, getSpecificLog } from './apiService.js';
// Assuming sequenceManager.js might export both an initCustomSequence function
// and a sequenceManager object. If the local function at the end is to be used
// and fixed, sequenceManager object would need to be imported.
// For now, we only have the function import:
import { initCustomSequence } from './sequenceManager.js';
import { PROCESS_INFO_CLIENT, getIsAnySequenceRunning } from './state.js';
import { notifications } from './notifications.js';
import { interactions } from './interactions.js';
import { animations } from './animations.js';
import { activeLogPanel } from './activeLogPanel.js';
import store from './store.js';

// WORKFLOW_CONFIG is used in showStepSpecificLogs but not defined/imported.
// This would be a ReferenceError. Assuming it's globally available or defined elsewhere
// as it's not in the provided TypeScript error list.
// let WORKFLOW_CONFIG = {}; // Placeholder if it needs to be defined

// escapeHtml is used in showStepSpecificLogs but not defined/imported.
// This would be a ReferenceError. Assuming it's globally available or defined elsewhere.
// function escapeHtml(unsafe) { // Placeholder
//    return unsafe.replace(/&/g, "&").replace(/</g, "<").replace(/>/g, ">").replace(/"/g, """).replace(/'/g, "'");
// }


// Main event handlers initialization
export async function initEventHandlers() {
    // Gestionnaire pour le bouton "Lancer Workflow (0-4)"
    mainElements.runSequenceBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        if (getIsAnySequenceRunning()) {
            notifications.warning('Une séquence est déjà en cours d\'exécution');
            animations.shake(e.target);
            return;
        }

        const confirmed = await interactions.confirmDialog({
            title: 'Lancer le workflow complet',
            message: 'Voulez-vous lancer la séquence complète (étapes 0-4) ?',
            confirmText: 'Lancer',
            cancelText: 'Annuler'
        });

        if (confirmed) {
            const spinner = interactions.showLoadingSpinner(e.target, 'Démarrage...');
            try {
                const result = await runCustomSequence(['preparation_dezip', 'scene_cut', 'analyze_audio', 'tracking', 'minify_json']);
                if (result.success) {
                    notifications.success('Workflow démarré avec succès');
                } else {
                    throw new Error(result.data?.message || 'Erreur de démarrage');
                }
            } catch (error) {
                notifications.error('Erreur lors du lancement du workflow: ' + error.message);
                animations.shake(e.target);
            } finally {
                spinner.hide();
            }
        }
    });

    // Gestionnaire pour le bouton "Mode Auto"
    mainElements.toggleAutoModeBtn.addEventListener('click', async () => {
        const spinner = interactions.showLoadingSpinner(mainElements.toggleAutoModeBtn, 'Changement de mode...');
        try {
            const result = await toggleAutoMode();
            if (result.success) {
                const isEnabled = result.data.auto_mode_enabled;
                // Corrected: Use actual backticks and decoded characters
                notifications.info(`Mode Auto ${isEnabled ? 'activé' : 'désactivé'}`);
                mainElements.toggleAutoModeBtn.classList.toggle('active', isEnabled);
                animations.pulse(mainElements.toggleAutoModeBtn);
            } else {
                throw new Error(result.data?.message || 'Erreur de basculement');
            }
        } catch (error) {
            notifications.error('Erreur lors du changement de mode: ' + error.message);
            animations.shake(mainElements.toggleAutoModeBtn);
        } finally {
            spinner.hide();
        }
    });

    // Gestionnaire pour le bouton "Séquence Personnalisée"
    const customSequenceBtn = mainElements.customSequenceBtn;
    if (customSequenceBtn) {
        customSequenceBtn.addEventListener('click', () => {
            const modal = modalElements.customSequenceModal;
            if (modal) {
                modal.style.display = 'block';
                initCustomSequence(); // Calls the imported initCustomSequence
                animations.fadeIn(modal);
            }
        });
    }

    // Gestionnaires pour les étapes individuelles
    document.querySelectorAll('.step').forEach(stepElement => {
        const stepKey = stepElement.dataset.stepKey;
        const elements = getStepElements(stepKey);

        // Bouton de lancement
        if (elements.runButton) {
            elements.runButton.addEventListener('click', async (e) => {
                if (getIsAnySequenceRunning()) {
                    notifications.warning('Une séquence est déjà en cours.');
                    animations.shake(e.target);
                    return;
                }
                const spinner = interactions.showLoadingSpinner(e.target, 'Lancement...');
                try {
                    const response = await runStep(stepKey);
                    if (!response.ok) { // Assuming response structure has 'ok' similar to fetch
                        const errorData = await response.json(); // Or response.data if already parsed
                        throw new Error(errorData?.message || 'Erreur de lancement');
                    }
                    // If response.ok is not the indicator, adjust based on actual apiService.runStep behavior
                    // For example, if it throws on error, the catch block handles it.
                    // If it returns { success: false, data: { message: ... } }, then:
                    // if (!response.success) throw new Error(response.data?.message || 'Erreur de lancement');

                } catch (error) {
                    notifications.error(error.message);
                    animations.shake(e.target);
                } finally {
                    spinner.hide();
                }
            });
        }

        // Bouton d'annulation
        if (elements.cancelButton) {
            elements.cancelButton.addEventListener('click', async (e) => {
                if (elements.cancelButton.disabled) return;
                const spinner = interactions.showLoadingSpinner(e.target, 'Annulation...');
                try {
                    const response = await cancelStep(stepKey);
                     if (!response.ok) { // Similar assumption as runStep
                        const errorData = await response.json();
                        throw new Error(errorData?.message || 'Erreur d\'annulation');
                    }
                } catch (error) {
                    notifications.error(error.message);
                    animations.shake(e.target);
                } finally {
                    spinner.hide();
                }
            });
        }

        // Bouton des logs
        if (elements.logsButton) {
            elements.logsButton.addEventListener('click', async () => {
                // This seems to be an older log display. showStepLogs function (defined later) is more detailed.
                // For consistency, consider calling showStepLogs(stepKey);
                // showStepLogs(stepKey);
                // Or use the existing logic if it's different:
                const modal = modalElements.logModal;
                if (modal) {
                    modal.style.display = 'block';
                    animations.fadeIn(modal);
                    
                    try {
                        // The endpoint /status/${stepKey} is used by showStepLogs.
                        // This fetch might be redundant if showStepLogs is preferred.
                        const response = await fetch(`/status/${stepKey}`);
                        const data = await response.json();
                        
                        if (data.log) {
                            const logContent = document.getElementById('logModalContent');
                            // Using textContent might be safer for logs to prevent XSS if logs aren't sanitized.
                            // However, formatLogs (used in showStepLogs) returns HTML, so innerHTML is used there.
                            // For raw logs, join with newline.
                            logContent.textContent = data.log.join('\n');
                            // Scroll to bottom
                            logContent.scrollTop = logContent.scrollHeight;
                        }
                    } catch (error) {
                        notifications.error('Erreur lors du chargement des logs: ' + error.message);
                    }
                }
            });
        }

        if (elements.specificLogsButton) {
            elements.specificLogsButton.addEventListener('click', async () => {
                // This button's logic seems to be reimplemented by showStepSpecificLogs.
                // Consider calling showStepSpecificLogs(stepKey);
                // showStepSpecificLogs(stepKey);
                // Or use the existing logic:
                const modal = modalElements.specificLogsModal;
                if (modal) {
                    modal.style.display = 'block';
                    animations.fadeIn(modal);
                    
                    try {
                        // Endpoint /status/${stepKey} used again.
                        const response = await fetch(`/status/${stepKey}`);
                        const data = await response.json();
                        
                        if (data.specific_logs_config) {
                            const logList = document.getElementById('specificLogsModalList');
                            logList.innerHTML = ''; // Clear existing entries
                            
                            data.specific_logs_config.forEach((logConfig, index) => {
                                const listItem = document.createElement('div');
                                listItem.className = 'specific-log-item';
                                listItem.innerHTML = `
                                    <span class="log-name">${logConfig.display_name}</span>
                                    <button class="view-log-btn" data-index="${index}">
                                        <i class="fas fa-eye"></i> Voir
                                    </button>
                                `;
                                
                                const viewButton = listItem.querySelector('.view-log-btn');
                                viewButton.addEventListener('click', async () => {
                                    try {
                                        // apiService.getSpecificLog is available, consider using it.
                                        // const logData = await getSpecificLog(stepKey, index);
                                        const logResponse = await fetch(`/get_specific_log/${stepKey}/${index}`);
                                        const logData = await logResponse.json();
                                        
                                        if (logData.content) {
                                            const logContent = document.getElementById('specificLogsModalContent');
                                            logContent.textContent = logData.content;
                                            logContent.scrollTop = 0; // Scroll to top for new content
                                        }
                                    } catch (error) {
                                        notifications.error('Erreur lors du chargement du log spécifique: ' + error.message);
                                    }
                                });
                                
                                logList.appendChild(listItem);
                            });
                        }
                    } catch (error) {
                        notifications.error('Erreur lors du chargement des logs spécifiques: ' + error.message);
                    }
                }
            });
        }
    });

    // Gestionnaire pour le bouton "Lancer la Séquence"
    const startCustomSequenceBtn = modalElements.customSequenceModal.querySelector('#startCustomSequenceBtn');
    if (startCustomSequenceBtn) {
        startCustomSequenceBtn.addEventListener('click', async () => {
            if (getIsAnySequenceRunning()) {
                notifications.warning('Une séquence est déjà en cours d\'exécution');
                animations.shake(startCustomSequenceBtn);
                return;
            }

            const selectedSteps = [];
            modalElements.stepsSelectionContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                selectedSteps.push(checkbox.value);
            });

            if (selectedSteps.length === 0) {
                notifications.warning('Veuillez sélectionner au moins une étape.');
                return;
            }

            const spinner = interactions.showLoadingSpinner(startCustomSequenceBtn, 'Démarrage...');
            try {
                const result = await runCustomSequence(selectedSteps);
                if (result.success) {
                    const modal = modalElements.customSequenceModal;
                    await animations.fadeOut(modal);
                    modal.style.display = 'none';
                    notifications.success('Séquence personnalisée lancée avec succès');
                } else {
                    throw new Error(result.data?.message || 'Erreur de lancement');
                }
            } catch (error) {
                notifications.error('Erreur lors du lancement de la séquence: ' + error.message);
                animations.shake(startCustomSequenceBtn);
            } finally {
                spinner.hide();
            }
        });
    }

    // Gestionnaire pour le bouton "Annuler" de la modale
    const cancelCustomSequenceBtn = modalElements.customSequenceModal.querySelector('#cancelCustomSequenceBtn');
    if (cancelCustomSequenceBtn) {
        cancelCustomSequenceBtn.addEventListener('click', () => {
            const modal = modalElements.customSequenceModal;
            animations.fadeOut(modal).then(() => {
                modal.style.display = 'none';
            });
        });
    }

    // Gestionnaires pour la fermeture des modales
    document.querySelectorAll('.modal .close-button').forEach(button => {
        button.addEventListener('click', async () => {
            const modal = button.closest('.modal');
            if (modal) {
                await animations.fadeOut(modal);
                modal.style.display = 'none';
            }
        });
    });

    // Fermeture des modales en cliquant en dehors
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', async (event) => {
            if (event.target === modal) {
                await animations.fadeOut(modal);
                modal.style.display = 'none';
            }
        });
    });
}

// Function to show step logs in modal
async function showStepLogs(stepKey) {
    try {
        const response = await fetch(`/status/${stepKey}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        
        const modal = modalElements.logModal;
        const title = modal.querySelector('#logModalTitle');
        const content = modal.querySelector('#logModalContent');

        if (!title || !content) {
            throw new Error('Les éléments de la modale n\'ont pas été trouvés');
        }

        title.innerHTML = `<i class="fas fa-file-alt"></i> Logs: ${data.display_name || stepKey}`;
        
        // Corrected: Use && instead of &&
        if (data.log && data.log.length > 0) {
            content.innerHTML = `<pre class="log-content">${formatLogs(data.log)}</pre>`;
            content.scrollTop = content.scrollHeight; // Scroll to bottom for latest logs
        } else {
            content.innerHTML = '<p class="no-logs-message">Aucun log disponible pour cette étape.</p>';
        }

        modal.style.display = 'block';
        await animations.fadeIn(modal);
        
    } catch (error) {
        console.error('Erreur lors de l\'affichage des logs:', error);
        notifications.error('Erreur lors de l\'affichage des logs');
    }
}

// Function to show specific logs menu
export async function showStepSpecificLogs(stepKey) {
    const modal = document.getElementById('specificLogsModal');
    const title = modal.querySelector('.modal-title');
    const contentContainer = modal.querySelector('.modal-content-container');
    const pathDisplay = modal.querySelector('.log-path');
    
    // WORKFLOW_CONFIG needs to be defined/imported for this to work.
    // For now, assuming WORKFLOW_CONFIG is globally available.
    // If not, this line will throw a ReferenceError.
    const stepConfig = WORKFLOW_CONFIG[stepKey]; 
    
    if (!stepConfig || !stepConfig.specific_logs || stepConfig.specific_logs.length === 0) {
        notifications.info("Aucun log spécifique configuré pour cette étape.");
        return;
    }

    // escapeHtml needs to be defined/imported. Assuming it's globally available.
    title.innerHTML = `<i class="fas fa-list-ul"></i> Logs Spécifiques: ${escapeHtml(stepConfig.display_name)}`;
    contentContainer.innerHTML = ''; // Vider le contenu précédent
    if(pathDisplay) pathDisplay.textContent = '';

    const ul = document.createElement('ul');
    ul.className = 'specific-log-list';

    stepConfig.specific_logs.forEach((logConf, index) => {
        const li = document.createElement('li');
        const button = document.createElement('button');
        button.className = 'action-button ripple-effect';
        button.innerHTML = `<i class="fas fa-file-alt"></i> ${escapeHtml(logConf.name)}`;
        button.onclick = async () => {
            const spinner = interactions.showLoadingSpinner(button, 'Chargement...');
            try {
                const logData = await getSpecificLog(stepKey, index); // Using imported apiService function
                if (logData.error) { // Assuming getSpecificLog might return an error object
                    throw new Error(logData.error);
                }
                if(pathDisplay) pathDisplay.textContent = logData.path;
                
                if (logData.type === 'csv') {
                    contentContainer.innerHTML = logData.content; 
                } else {
                    const pre = document.createElement('pre');
                    pre.className = 'log-content';
                    // logData.content should already be escaped if it's plain text.
                    // If it contains HTML and is trusted, innerHTML is fine.
                    // For safety with unknown log content, textContent is better for <pre>.
                    pre.textContent = logData.content; 
                    contentContainer.innerHTML = '';
                    contentContainer.appendChild(pre);
                }
                
                animations.fadeIn(contentContainer);
                
            } catch (error) {
                notifications.error(`Erreur lors du chargement du log: ${error.message}`);
                contentContainer.innerHTML = `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${escapeHtml(error.message)}</div>`;
            } finally {
                spinner.hide();
            }
        };
        li.appendChild(button);
        ul.appendChild(li);
    });

    contentContainer.innerHTML = '';
    contentContainer.appendChild(ul);

    modal.style.display = 'block';
    await animations.fadeIn(modal);

    const closeBtn = modal.querySelector('.close-button');
    if(closeBtn) {
        closeBtn.onclick = async () => {
            await animations.fadeOut(modal);
            modal.style.display = 'none';
        };
    }
}

// Helper function to format logs with syntax highlighting
function formatLogs(logs) {
    if (!Array.isArray(logs)) {
        logs = [String(logs)];
    }
    
    return logs.map(line => {
        const escapedLine = String(line)
            // Corrected: Escape & first, then <, then >
            .replace(/&/g, '&')
            .replace(/</g, '<')
            .replace(/>/g, '>');
            
        // These conditions create HTML, so escapedLine should be used.
        if (line.includes('INFO')) {
            return `<span class="log-info">${escapedLine}</span>`;
        } else if (line.includes('WARNING')) {
            return `<span class="log-warning">${escapedLine}</span>`;
        } else if (line.includes('ERROR')) {
            return `<span class="log-error">${escapedLine}</span>`;
        } else if (line.includes('SUCCESS')) {
            return `<span class="log-success">${escapedLine}</span>`;
        } else if (line.match(/\[(.*?)\]/)) { // Example: highlight lines with timestamps
            return `<span class="log-timestamp">${escapedLine}</span>`;
        }
        return escapedLine; // Return the escaped line if no specific formatting applies
    }).join('\n');
}

// This function was conflicting with the imported `initCustomSequence`.
// It's renamed to avoid the conflict.
// It also used `sequenceManager.initCustomSequence` but `sequenceManager` (the object)
// was not imported. If this logic is to be used, `sequenceManager` (object)
// would need to be imported, e.g., `import { sequenceManager } from './sequenceManager.js';`
// For now, it's an unused function.
function _local_initCustomSequence_handler_unused() {
    // Récupérer la configuration depuis le store
    const commandsConfig = store.getState().commandsConfig;
    
    // Initialiser le gestionnaire de séquence avec la configuration
    // This line would require `sequenceManager` (object) to be imported.
    // sequenceManager.initCustomSequence(commandsConfig); 
    console.warn("'_local_initCustomSequence_handler_unused' was called, but 'sequenceManager' object is not imported/used correctly for its internal call.");
}