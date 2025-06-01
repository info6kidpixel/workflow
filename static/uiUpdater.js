import { PROCESS_INFO_CLIENT, setIsAnySequenceRunning } from './state.js';
import { STEP_STATES, STATE_CLASSES, STATUS_MESSAGES } from './constants.js';
import { gpuManager } from './gpuManager.js';
import { formatDuration } from './utils.js';
import { animations } from './animations.js';

export function updateStepUI(stepElement, data) {
    if (!stepElement) return;
    
    const elements = {
        statusText: stepElement.querySelector('.status-text'),
        progressBar: stepElement.querySelector('.progress-bar'),
        progressText: stepElement.querySelector('.progress-text'),
        runButton: stepElement.querySelector('.run-button'),
        cancelButton: stepElement.querySelector('.cancel-button'),
        showLogButton: stepElement.querySelector('.show-log-button'),
        showSpecificLogsButton: stepElement.querySelector('.show-specific-logs-button'),
        gpuStatus: stepElement.querySelector('.gpu-status'),
        container: stepElement
    };

    const previousStatus = stepElement.dataset.status;
    stepElement.dataset.status = data.status;
    updateStepStatus(elements, data.status, previousStatus);
    // Correction : passer previousStatus à updateStepControls
    updateStepControls(elements, data, previousStatus);
    updateStepProgress(elements, data);
    
    // Gestion du badge GPU (corrigé pour .gpu-status-badge)
    const gpuBadgeContainer = stepElement.querySelector('.gpu-status-badge');
    if (gpuBadgeContainer) {
        if (data.gpu_intensive) {
            let badgeHtml;
            let stateText = "disponible";
            let stateIcon = "fa-check-circle";
            let stateClass = "available";

            if (data.status === 'running' && data.gpu_intensive) {
                stateText = "GPU actif";
                stateIcon = "fa-cogs";
                stateClass = "running";
            } else if (data.status === 'pending_gpu') {
                stateText = "Attente GPU";
                stateIcon = "fa-clock";
                stateClass = "waiting";
            }

            badgeHtml = `
                <span class="gpu-label">
                    <i class="fas fa-microchip"></i> GPU
                </span>
                <span class="separator"></span>
                <span class="gpu-state ${stateClass}">
                    <i class="fas ${stateIcon}"></i> ${stateText}
                </span>
            `;
            gpuBadgeContainer.innerHTML = badgeHtml;
            gpuBadgeContainer.style.display = 'flex';
        } else {
            gpuBadgeContainer.style.display = 'none';
        }
    }
    
    // Update specific logs button
    updateSpecificLogsButton(elements, data);
    
    // Handle sequence mode specific UI updates
    if (data.is_any_sequence_running) {
        handleSequenceMode(elements.container, data, previousStatus);
    }
}

function updateStepStatus(elements, status, previousStatus) {
    const { container, statusText } = elements;
    
    // Remove old status classes
    Object.values(STATE_CLASSES).forEach(className => {
        container.classList.remove(className);
    });
    
    // Add new status class
    const newStatusClass = STATE_CLASSES[status] || STATE_CLASSES.idle;
    container.classList.add(newStatusClass);
    
    // Update status text and animate if changed
    // Remplacer fadeTransition par fadeText si utilisé
    if (statusText) {
        const newStatusMsg = STATUS_MESSAGES[status] || status;
        if (status !== previousStatus) {
            animations.fadeText(statusText, newStatusMsg);
        } else {
            statusText.textContent = newStatusMsg;
        }
    }
}

function updateStepControls(elements, data, previousStatus) {
    const { runButton, cancelButton, showLogButton } = elements;
    
    if (runButton) {
        const isRunnable = !data.is_any_sequence_running && 
                          ['idle', 'completed', 'error', 'cancelled', 'failed'].includes(data.status);
        runButton.disabled = !isRunnable;
        runButton.title = getRunButtonTooltip(data);
        
        if (data.status === 'completed') {
            animations.success(runButton);
        } else if (data.status === 'error' || data.status === 'failed') {
            // Correction : animations.error n'existe pas, utiliser animations.shake
            animations.shake(runButton);
        }
    }
    
    if (cancelButton) {
        const isCancellable = ['running', 'pending_gpu', 'starting', 'initiated'].includes(data.status);
        if (isCancellable) {
            animations.fadeIn(cancelButton);
            cancelButton.style.display = 'inline-flex';
        } else {
            animations.fadeOut(cancelButton).then(() => {
                cancelButton.style.display = 'none';
            });
        }
        cancelButton.disabled = !isCancellable;
    }
    
    if (showLogButton) {
        const hasLogs = data.log && data.log.length > 0;
        showLogButton.style.display = hasLogs ? 'inline-flex' : 'none';
        if (hasLogs && data.status !== previousStatus && typeof animations.pulse === 'function') {
            animations.pulse(showLogButton);
        }
    }
}

function updateStepProgress(elements, data) {
    const { progressBar, progressText } = elements;
    
    if (progressBar) {
        const progress = data.progress_total > 0 
            ? Math.round((data.progress_current / data.progress_total) * 100) 
            : 0;
        
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        
        if (['running', 'starting'].includes(data.status) && !progressBar.classList.contains('progress-animated')) {
            progressBar.classList.add('progress-animated');
        } else if (!['running', 'starting'].includes(data.status)) {
            progressBar.classList.remove('progress-animated');
        }
    }
    
    if (progressText) {
        const text = getProgressText(data);
        if (text !== progressText.textContent) {
            animations.fadeTransition(progressText, text);
        }
    }
}

function updateGpuStatus(elements, data) {
    const { gpuStatus } = elements;
    
    if (!gpuStatus) return;

    const badgeDetails = gpuManager.getGpuBadgeDetails(data.gpu_status, data.gpu_intensive);
    
    if (badgeDetails) {
        // Update badge content and style
        const badgeContent = `<i class="fas ${badgeDetails.icon}"></i> ${badgeDetails.text}`;
        if (gpuStatus.innerHTML !== badgeContent) {
            animations.fadeTransition(gpuStatus, badgeContent);
        }
        
        // Update classes
        gpuStatus.className = badgeDetails.className;
        
        // Apply pulse animation if needed
        if (badgeDetails.shouldPulse) {
            animations.pulse(gpuStatus);
        }
        
        gpuStatus.style.display = 'inline-flex';
    } else if (gpuStatus) {
        gpuStatus.style.display = 'none';
    }
}

function updateSpecificLogsButton(elements, data) {
    const { showSpecificLogsButton } = elements;
    
    if (showSpecificLogsButton) {
        const hasSpecificLogs = data.specific_logs_config && data.specific_logs_config.length > 0;
        if (hasSpecificLogs) {
            animations.fadeIn(showSpecificLogsButton);
            showSpecificLogsButton.style.display = 'inline-flex';
        } else {
            animations.fadeOut(showSpecificLogsButton).then(() => {
                showSpecificLogsButton.style.display = 'none';
            });
        }
    }
}

function handleSequenceMode(element, data, previousStatus) {
    if (data.status === 'running' && previousStatus !== 'running') {
        element.classList.add('sequence-active-step');
        animations.highlight(element);
    } else if (data.status !== 'running' && previousStatus === 'running') {
        element.classList.remove('sequence-active-step');
        if (data.status === 'completed') {
            animations.success(element);
        } else if (data.status === 'error' || data.status === 'failed') {
            animations.error(element);
        }
    }
}

function getRunButtonTooltip(data) {
    if (data.is_any_sequence_running) {
        return "Une séquence est en cours d'exécution";
    }
    return 'Lancer cette étape';
}

function getProgressText(data) {
    if (!data.progress_text && !data.progress_total) return '';
    
    if (data.progress_text) {
        return data.progress_text;
    }
    
    if (data.progress_total > 0) {
        return `${data.progress_current}/${data.progress_total}`;
    }
    
    return '';
}

export function updateAllStepsUI(stepsData) {
    Object.keys(stepsData).forEach(stepKey => {
        const stepElement = document.querySelector(`[data-step-key="${stepKey}"]`);
        if (stepElement) {
            updateStepUI(stepElement, stepsData[stepKey]);
        }
    });
}