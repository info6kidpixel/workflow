import { updateStepUI } from './uiUpdater.js';
import { updateGpuInfoPanel } from './gpuInfoPanel.js';
import { PROCESS_INFO_CLIENT, getUserManuallyClosedActiveLogPanel, setUserManuallyClosedActiveLogPanel, setIsAnySequenceRunning } from './state.js';
import { activeLogPanel } from './activeLogPanel.js';
import { animations } from './animations.js';
import store from './store.js';

let currentSequenceStep = null;
let lastSequenceUpdate = null;

export async function pollStepStatus(stepKey) {
    try {
        const response = await fetch(`/status/${stepKey}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        
        const stepElement = document.querySelector(`[data-step-key="${stepKey}"]`);
        if (stepElement) {
            const previousStatus = PROCESS_INFO_CLIENT[stepKey]?.status;
            const previousSequenceState = PROCESS_INFO_CLIENT[stepKey]?.is_any_sequence_running;
            
            // Mettre à jour l'UI avec animation
            await updateStepUI(stepElement, data);
            if (data.status !== previousStatus) {
                animations.pulse(stepElement);
            }
            updateGpuInfoPanel();

            // Gérer l'affichage automatique des logs pour les séquences
            if (data.is_any_sequence_running) {
                // Mettre à jour la barre de progression de la séquence si nécessaire
                if (data.sequence_progress) {
                    updateSequenceProgress(data.sequence_progress);
                }

                if (data.status === 'running' && (previousStatus !== 'running' || currentSequenceStep !== stepKey)) {
                    // Nouvelle étape active dans la séquence
                    setUserManuallyClosedActiveLogPanel(false);
                    currentSequenceStep = stepKey;
                    await updateSequenceLogs(stepKey, data);
                    
                    // Animation de l'étape active
                    stepElement.classList.add('sequence-active-step');
                    animations.highlight(stepElement);
                    
                    // Notification avec temps estimé si disponible
                    const estimatedTime = data.estimated_time ? ` (durée estimée: ${data.estimated_time})` : '';
                    notifications.info(`Démarrage de l'étape "${data.display_name}"${estimatedTime}`);
                } else if (data.status === 'running' && currentSequenceStep === stepKey) {
                    // Mise à jour des logs de l'étape en cours
                    const userClosed = getUserManuallyClosedActiveLogPanel();
                    await updateSequenceLogs(stepKey, data, !userClosed);
                    
                    // Mettre à jour le temps écoulé si disponible
                    if (data.elapsed_time) {
                        updateElapsedTime(stepElement, data.elapsed_time);
                    }
                } else if (data.status === 'completed' && currentSequenceStep === stepKey) {
                    // Animation de complétion
                    animations.success(stepElement);
                    stepElement.classList.remove('sequence-active-step');
                    
                    // Garder les logs affichés brièvement
                    setTimeout(async () => {
                        if (currentSequenceStep === stepKey) {
                            await fadeOutLogs();
                        }
                    }, 3000);
                }
            } else if (!data.is_any_sequence_running && previousSequenceState) {
                // La séquence est terminée
                handleSequenceCompletion(stepKey, data);
            }

            // Gérer les changements d'état
            handleStatusChange(stepKey, data, previousStatus);
            
            // Mettre à jour le state
            PROCESS_INFO_CLIENT[stepKey] = data;
            lastSequenceUpdate = Date.now();
        }
    } catch (error) {
        console.error(`Erreur lors du polling pour ${stepKey}:`, error);
        handlePollingError(stepKey, error);
    }
}

async function updateSequenceLogs(stepKey, data, openPanel = true) {
    try {
        if (openPanel) {
            await activeLogPanel.show(stepKey, data.display_name);
        }
        
        // Formater et mettre à jour les logs avec coloration et animations
        const formattedLog = formatLogWithSyntaxHighlighting(data.log);
        activeLogPanel.updateMainLog(formattedLog);
        
        // Mise à jour des logs spécifiques si disponibles
        if (data.specific_logs && data.specific_logs.length > 0) {
            const logData = await getSpecificLog(stepKey, 0);
            if (!logData.error) {
                const formattedSpecificLog = formatLogWithSyntaxHighlighting(logData.content);
                activeLogPanel.updateSpecificLog(formattedSpecificLog);
            }
        }
    } catch (error) {
        console.error('Erreur lors de la mise à jour des logs :', error);
        notifications.error('Erreur lors de la mise à jour des logs');
    }
}

function formatLogWithSyntaxHighlighting(log) {
    return log
        .map(line => {
            if (line.includes('INFO')) {
                return `<span class="log-info">${line}</span>`;
            } else if (line.includes('WARNING')) {
                return `<span class="log-warning">${line}</span>`;
            } else if (line.includes('ERROR')) {
                return `<span class="log-error">${line}</span>`;
            } else if (line.includes('SUCCESS')) {
                return `<span class="log-success">${line}</span>`;
            } else if (line.match(/\[(.*?)\]/)) {
                return `<span class="log-timestamp">${line}</span>`;
            }
            return line;
        })
        .join('<br>');
}

async function fadeOutLogs() {
    await animations.fadeOut(activeLogPanel.getElement());
    currentSequenceStep = null;
    await activeLogPanel.hide();
    setUserManuallyClosedActiveLogPanel(false);
}

function updateSequenceProgress(progress) {
    const progressBar = document.querySelector('.sequence-progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
    }
}

function updateElapsedTime(element, elapsed) {
    const timeElement = element.querySelector('.elapsed-time');
    if (timeElement) {
        timeElement.textContent = elapsed;
    }
}

// Show sequence summary in modal with proper error handling
async function showSequenceSummary(sequenceOutcome) {
    console.log("Showing sequence summary for outcome:", sequenceOutcome);
    const modal = document.getElementById('sequenceSummaryModal');
    if (!modal) {
        console.error("Summary modal not found");
        return;
    }
    
    // Utiliser les IDs corrects du HTML
    const titleEl = modal.querySelector('#sequenceSummaryTitle span');
    const titleIconEl = modal.querySelector('#sequenceSummaryTitle i');
    const timestampEl = modal.querySelector('#sequenceTimestamp span');
    const durationEl = modal.querySelector('#sequenceDuration span');
    const stepsSummaryEl = modal.querySelector('#stepsSummary'); // Corrigé
    const errorMsgEl = modal.querySelector('#sequenceError');    // Corrigé
    const viewLogsBtn = modal.querySelector('.action-button.view-logs');
    
    if (!titleEl || !titleIconEl || !timestampEl || !stepsSummaryEl || !errorMsgEl || !viewLogsBtn) {
        console.error('Missing required modal elements');
        return;
    }
    
    // Reset content
    stepsSummaryEl.innerHTML = '';
    errorMsgEl.style.display = 'none';
    viewLogsBtn.style.display = 'none';
    
    // Format status display
    const sequenceStatus = sequenceOutcome.status;
    const sequenceType = sequenceOutcome.type || "Inconnu";
    const sequenceMessage = sequenceOutcome.message || "Aucun message de résumé.";
    const sequenceTimestamp = sequenceOutcome.timestamp ? 
        new Date(sequenceOutcome.timestamp).toLocaleString('fr-FR') : 
        "Date inconnue";
    
    // Update title and icon based on status
    let titleText, titleIconClass;
    switch (sequenceStatus) {
        case "success":
            titleText = `Séquence ${sequenceType} Terminée avec Succès`;
            titleIconClass = 'fas fa-check-circle text-success';
            break;
        case "cancelled":
            titleText = `Séquence ${sequenceType} Annulée par l'Utilisateur`;
            titleIconClass = 'fas fa-ban text-warning';
            break;
        case "error":
        case "failed":
            titleText = `Séquence ${sequenceType} Échouée`;
            titleIconClass = 'fas fa-exclamation-circle text-danger';
            break;
        default:
            titleText = `Séquence ${sequenceType} - État: ${sequenceStatus}`;
            titleIconClass = 'fas fa-info-circle text-info';
    }
    
    titleEl.textContent = titleText;
    titleIconEl.className = titleIconClass;
    
    // Update timestamp and duration
    timestampEl.textContent = `${sequenceTimestamp}`;
    if (sequenceOutcome.duration) {
        durationEl.textContent = `Durée: ${sequenceOutcome.duration}`;
        durationEl.parentElement.style.display = 'block';
    } else {
        durationEl.parentElement.style.display = 'none';
    }
    
    // Parse and display step information
    if (sequenceMessage && sequenceMessage.includes('|')) {
        const steps = sequenceMessage.split('|').map(step => step.trim()).filter(Boolean);
        steps.forEach((step, index) => {
            const stepDiv = document.createElement('div');
            stepDiv.className = 'step-summary';
            stepDiv.style.opacity = '0';
            stepDiv.style.transform = 'translateY(20px)';
            
            const [stepName, stepStatus] = step.split(':').map(s => s.trim());
            const statusClass = stepStatus?.toLowerCase().includes('succès') ? 'text-success' :
                              stepStatus?.toLowerCase().includes('annul') ? 'text-warning' : 'text-danger';
            
            stepDiv.innerHTML = `
                <span class="step-name">${stepName}</span>
                <span class="step-status ${statusClass}">${stepStatus || 'Non exécutée'}</span>
            `;
            
            stepsSummaryEl.appendChild(stepDiv);
            
            // Animate step entry
            setTimeout(() => {
                stepDiv.style.transition = 'all 0.3s ease';
                stepDiv.style.opacity = '1';
                stepDiv.style.transform = 'translateY(0)';
            }, index * 100);
        });
    } else {
        // Single message display if no step breakdown
        const messageDiv = document.createElement('div');
        messageDiv.className = 'summary-message';
        messageDiv.textContent = sequenceMessage;
        stepsSummaryEl.appendChild(messageDiv);
    }
    
    // Show error section if needed
    if ((sequenceStatus === "error" || sequenceStatus === "failed") && sequenceMessage) {
        errorMsgEl.style.display = 'block';
        errorMsgEl.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            <span>Erreur principale: ${sequenceMessage.split('.')[0]}</span>
        `;
    }
    
    // Configure logs button for error/cancelled cases
    const lastRelevantStep = sequenceOutcome.last_active_step_in_sequence_if_error;
    if (lastRelevantStep && PROCESS_INFO_CLIENT[lastRelevantStep]) {
        viewLogsBtn.style.display = 'inline-flex';
        viewLogsBtn.onclick = () => showStepLogs(lastRelevantStep);
    }
    
    // Show modal with animation
    modal.style.display = 'flex';
    await animations.fadeIn(modal);
    
    // Setup close handler
    const closeButtons = modal.querySelectorAll('.close-button, .action-button.close');
    closeButtons.forEach(button => {
        button.onclick = async () => {
            await animations.fadeOut(modal);
            modal.style.display = 'none';
        };
    });
}

// Handle sequence completion and show summary
async function handleSequenceCompletion(stepKey, data) {
    currentSequenceStep = null;
    
    // Préparer les données pour le résumé
    const summaryData = {
        success: data.status !== 'failed',
        total_duration: data.total_duration || 0,
        last_step_key: stepKey,
        error_message: data.error_message,
        steps: data.sequence_steps || [],
        type: data.last_sequence_outcome?.type || 'Séquence'
    };
    
    // Afficher le résumé après un court délai pour laisser les animations se terminer
    setTimeout(() => {
        showSequenceSummary(summaryData);
    }, 500);
    
    if (data.status === 'failed') {
        const userClosed = getUserManuallyClosedActiveLogPanel();
        if (!userClosed) {
            updateSequenceLogs(stepKey, data, true);
            notifications.error('La séquence a échoué. Consultez les logs pour plus de détails.');
        }
    } else {
        fadeOutLogs();
        animations.success(document.querySelector('.sequence-container'));
        notifications.success(`${summaryData.type} terminée avec succès !`);
    }
    
    // Réinitialiser l'interface
    document.querySelectorAll('.sequence-active-step').forEach(el => {
        el.classList.remove('sequence-active-step');
    });
}

function handleStatusChange(stepKey, data, previousStatus) {
    if (previousStatus === data.status) return;
    
    const statusMessages = {
        completed: `Étape "${data.display_name}" terminée avec succès`,
        failed: `Échec de l'étape "${data.display_name}"`,
        running: `Exécution de l'étape "${data.display_name}"`,
        waiting: `En attente de l'étape "${data.display_name}"`
    };
    
    if (statusMessages[data.status]) {
        notifications[data.status === 'failed' ? 'error' : data.status === 'completed' ? 'success' : 'info'](
            statusMessages[data.status]
        );
    }
}

function handlePollingError(stepKey, error) {
    if (Date.now() - lastSequenceUpdate > 5000) {
        notifications.error(`Erreur de communication avec le serveur pour l'étape "${stepKey}"`);
    }
}

export async function runStep(stepKey) {
    try {
        const response = await fetch(`/run/${stepKey}`, { method: 'POST' });
        const data = await response.json();
        return { success: response.ok, data };
    } catch (error) {
        console.error(`Erreur lors du lancement de ${stepKey}:`, error);
        return { success: false, error };
    }
}

export async function cancelStep(stepKey) {
    try {
        const response = await fetch(`/cancel/${stepKey}`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            currentSequenceStep = null; // Réinitialiser l'étape courante
        }
        return { success: response.ok, data };
    } catch (error) {
        console.error(`Erreur lors de l'annulation de ${stepKey}:`, error);
        return { success: false, error };
    }
}

export async function runCustomSequence(steps) {
    try {
        const response = await fetch('/run_sequence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ steps })
        });

        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                errorData = { message: response.statusText };
            }
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        setIsAnySequenceRunning(true); // Utiliser le setter

        return {
            success: true,
            data
        };
    } catch (error) {
        console.error('Erreur lors du lancement de la séquence:', error);
        return {
            success: false,
            data: {
                message: error.message
            }
        };
    }
}

export async function toggleAutoMode() {
    try {
        const response = await fetch('/api/toggle_auto_mode', { method: 'POST' });
        const data = await response.json();
        return { success: response.ok, data };
    } catch (error) {
        console.error('Erreur lors du basculement du mode auto:', error);
        return { success: false, error };
    }
}

export async function getSpecificLog(stepKey, logIndex) {
    try {
        const response = await fetch(`/get_specific_log/${stepKey}/${logIndex}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`Erreur lors de la récupération du log spécifique pour ${stepKey}:`, error);
        return { error: error.message };
    }
}

// Fetch COMMANDS_CONFIG from backend
export async function fetchCommandsConfig() {
    try {
        const response = await fetch('/api/get_commands_config');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('Erreur lors du chargement de COMMANDS_CONFIG:', error);
        return null;
    }
}

export async function getProcessInfoAndSyncStore() {
    try {
        const response = await fetch('/api/get_process_info');
        if (!response.ok) throw new Error('Erreur lors de la récupération des infos de processus');
        const data = await response.json();
        store.setState({ processInfo: data });
        return data;
    } catch (error) {
        console.error('Erreur getProcessInfoAndSyncStore:', error);
        return null;
    }
}
