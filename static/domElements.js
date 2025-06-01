// Éléments de l'interface principale
export const mainElements = {
    runSequenceBtn: document.getElementById('runSequenceBtn'),
    toggleAutoModeBtn: document.getElementById('toggleAutoMode'),
    customSequenceBtn: document.getElementById('customSequenceBtn'),
    localDownloadsContainer: document.getElementById('localDownloadsContainer')
};

// Éléments des modales
export const modalElements = {
    logModal: document.getElementById('logModal'),
    specificLogsModal: document.getElementById('specificLogsModal'),
    customSequenceModal: document.getElementById('customSequenceModal'),
    logModalContent: document.getElementById('logModalContent'),
    specificLogsModalContent: document.getElementById('specificLogsModalContent'),
    stepsSelectionContainer: document.getElementById('stepsSelectionContainer')
};

// Éléments du panneau GPU
export const gpuElements = {
    gpuInfoPanel: document.querySelector('.gpu-info-panel'),
    currentGpuStatus: document.getElementById('current-gpu-status'),
    currentGpuUser: document.getElementById('current-gpu-user'),
    gpuWaitingTasks: document.getElementById('gpu-waiting-tasks'),
    lastUpdate: null
};

// Fonction utilitaire pour obtenir les éléments d'une étape
export function getStepElements(stepKey) {
    const stepElement = document.querySelector(`[data-step-key="${stepKey}"]`);
    if (!stepElement) return null;

    return {
        container: stepElement,
        statusText: stepElement.querySelector('.status-text'),
        progressBar: stepElement.querySelector('.progress-bar'),
        progressText: stepElement.querySelector('.progress-text'),
        runButton: stepElement.querySelector('.run-button'),
        cancelButton: stepElement.querySelector('.cancel-button'),
        showLogButton: stepElement.querySelector('.show-log-button'),
        showSpecificLogsButton: stepElement.querySelector('.show-specific-logs-button'),
        logPanel: stepElement.querySelector('.log-panel'),
        logContent: stepElement.querySelector('.log-content'),
        gpuBadge: stepElement.querySelector('.gpu-intensive-badge'),
        gpuStatus: stepElement.querySelector('.gpu-status')
    };
}

// Fonction pour créer un élément avec des attributs et du contenu
export function createElement(tag, attributes = {}, content = '') {
    const element = document.createElement(tag);
    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            element.className = value;
        } else {
            element.setAttribute(key, value);
        }
    });
    if (content) element.textContent = content;
    return element;
}
