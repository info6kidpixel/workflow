// Ensure this line and any similar markers are NOT in your actual main.js file.
// --- START OF FILE main.js --- // <--- DELETE THIS LINE IF PRESENT IN YOUR FILE

import { initEventHandlers } from './eventHandlers.js';
import { initGpuInfoPanel, updateGpuInfoPanel } from './gpuInfoPanel.js';
import { pollStepStatus, fetchCommandsConfig } from './apiService.js';
import { addPollingInterval, getIsAnySequenceRunning, setAutoModeEnabled, setIsAnySequenceRunning } from './state.js';
import { notifications } from './notifications.js';
import { animations } from './animations.js';
import { errorLogger } from './errorLogger.js';
import { performanceMonitor } from './performanceMonitor.js';
import { mainElements } from './domElements.js';
import { initCustomSequence } from './sequenceManager.js';
import store from './store.js';

/**
 * Initialise le mode auto en vérifiant son état actuel
 */
async function initializeAutoMode() {
    try {
        const response = await fetch('/api/get_auto_mode_status');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Mettre à jour l'état du mode auto
        setAutoModeEnabled(data.auto_mode_enabled);
        setIsAnySequenceRunning(data.is_any_sequence_running_globally);
        
        // Mettre à jour l'interface utilisateur
        const toggleAutoMode = document.getElementById('toggleAutoMode');
        if (toggleAutoMode) {
            toggleAutoMode.checked = data.auto_mode_enabled;
            
            // Mettre à jour la classe du conteneur parent
            const switchContainer = toggleAutoMode.closest('.switch-container');
            if (switchContainer) {
                if (data.auto_mode_enabled) {
                    switchContainer.classList.add('active');
                    switchContainer.classList.remove('inactive');
                } else {
                    switchContainer.classList.add('inactive');
                    switchContainer.classList.remove('active');
                }
            }
        }
        
        console.log('Mode Auto initialisé avec succès:', data);
        return data;
    } catch (error) {
        console.error('Erreur lors de l'initialisation du mode auto:', error);
        errorLogger.logError({
            type: 'AUTO_MODE_INIT_ERROR',
            message: error.message,
            stack: error.stack,
            component: 'AutoMode'
        });
        throw error;
    }
}

function updateSequenceButtons(isSequenceRunning) {
    const buttons = document.querySelectorAll('.sequence-button');
    buttons.forEach(button => {
        button.disabled = isSequenceRunning;
        if (isSequenceRunning) {
            button.setAttribute('title', "Une séquence est en cours d'exécution"); // Corrected
        } else {
            button.removeAttribute('title');
        }
    });
}

function highlightActiveAutoModeStep(stepKey) {
    const stepElement = document.querySelector(`[data-step-key="${stepKey}"]`);
    if (stepElement) {
        animations.highlight(stepElement);
        stepElement.classList.add('auto-mode-active-step');
        
        // Scroll l'étape en cours dans la vue si nécessaire
        stepElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', async () => {
    console.log("Initialisation de l'application..."); // Corrected
    // Charger la configuration des commandes depuis le backend et la stocker dans le store
    try {
        const commandsConfig = await fetchCommandsConfig();
        if (commandsConfig) {
            store.setState({ commandsConfig });
        } else {
            console.error("Impossible de charger la configuration des étapes (COMMANDS_CONFIG) depuis le backend."); // Corrected
        }
    } catch (error) {
        console.error("Erreur lors du chargement de la configuration des étapes:", error); // Corrected
    }
    
    try {
        // Initialisation des gestionnaires d'événements
        await initEventHandlers();
        console.log("Gestionnaires d'événements initialisés"); // Corrected
        
        // Initialisation du panneau GPU
        initGpuInfoPanel();
        console.log('Panneau GPU initialisé');
        
        // Initialisation du mode auto
        await initializeAutoMode();
        console.log('Mode Auto initialisé');
        
        // Configuration du monitoring des performances (optionnel)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.log('Mode développement détecté, démarrage du moniteur de performance');
            performanceMonitor.start();
        }

    } catch (error) {
        errorLogger.logError({
            type: 'INIT_ERROR',
            message: `Erreur lors de l'initialisation: ${error.message}`,
            stack: error.stack,
            component: 'Initialization'
        });
        console.error("Erreur lors de l'initialisation:", error); // Corrected
        notifications.error("Erreur lors de l'initialisation de l'application"); // Corrected
    }

    // Polling global pour le statut du mode auto et GPU
    setInterval(async () => {
        try {
            const response = await fetch('/api/get_auto_mode_status');
            if (!response.ok) return;
            const data = await response.json();
            setIsAnySequenceRunning(data.is_any_sequence_running_globally);
            updateGpuInfoPanel(); // Force une mise à jour globale du panneau GPU
        } catch (error) {
            console.warn("Erreur lors du polling du statut global:", error);
            errorLogger.logError({
                type: 'GLOBAL_POLLING_ERROR',
                message: error.message,
                stack: error.stack,
                component: 'GlobalPolling'
            });
        }
    }, 5000); // Toutes les 5 secondes
    
    // Démarrage du polling pour chaque étape
    document.querySelectorAll('.step').forEach(stepElement => {
        const stepKey = stepElement.dataset.stepKey;
        
        // Premier appel immédiat pour récupérer l'état initial
        pollStepStatus(stepKey).catch(err => {
            console.warn(`Erreur polling initial ${stepKey}:`, err);
            errorLogger.logError({
                type: 'POLLING_ERROR',
                message: err.message,
                stack: err.stack,
                component: `Polling_${stepKey}`
            });
        });
        
        // Configuration du polling régulier
        const intervalId = setInterval(() => {
            pollStepStatus(stepKey).catch(err => {
                console.warn(`Erreur polling ${stepKey}:`, err);
                errorLogger.logError({
                    type: 'POLLING_ERROR',
                    message: err.message,
                    stack: err.stack,
                    component: `Polling_${stepKey}`
                });
            });
        }, 2000);
        
        addPollingInterval(stepKey, intervalId);
    });
});

// Exemple d'utilisation du store pour centraliser l'état processInfo
store.subscribe(state => {
    // Mettre à jour l'UI ou déclencher des actions selon l'état global
    // Par exemple :
    // if (state.isLoading) { ... }
});

// Pour mettre à jour l'état global depuis n'importe quel module :
// store.setState({ processInfo: newProcessInfo });

// Assurez-vous que ce code est exécuté après le chargement du DOM
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM chargé, initialisation des gestionnaires d'événements..."); // Corrected
    
    // Bouton "Lancer Workflow (0-4)"
    const runSequenceBtn = document.getElementById('runSequenceBtn');
    if (runSequenceBtn) {
        console.log("Bouton runSequenceBtn trouvé, ajout du gestionnaire d'événements"); // Corrected
        runSequenceBtn.addEventListener('click', function() {
            console.log('Clic sur Lancer Workflow');
            // Appeler la fonction qui lance la séquence
            // Par exemple: launchDefaultSequence();
        });
    } else {
        console.error('Bouton runSequenceBtn non trouvé dans le DOM');
    }
    
    // Toggle "Mode Auto"
    const toggleAutoMode = document.getElementById('toggleAutoMode');
    if (toggleAutoMode) {
        console.log("Toggle toggleAutoMode trouvé, ajout du gestionnaire d'événements"); // Corrected
        toggleAutoMode.addEventListener('change', function() {
            console.log('Changement de Mode Auto:', this.checked);
            // Appeler la fonction qui gère le changement de mode
            // Par exemple: toggleAutoModeState(this.checked);
        });
    } else {
        console.error('Toggle toggleAutoMode non trouvé dans le DOM');
    }
    
    // Bouton "Séquence Personnalisée"
    // Note: Ce bouton utilise déjà onclick dans le HTML, mais nous pouvons aussi l'attacher ici
    const customSequenceBtn = document.getElementById('customSequenceBtn');
    if (customSequenceBtn) {
        console.log('Bouton customSequenceBtn trouvé');
        // Si vous préférez utiliser addEventListener au lieu de onclick dans le HTML:
        /*
        customSequenceBtn.addEventListener('click', function() {
            console.log('Clic sur Séquence Personnalisée');
            document.getElementById('customSequenceModal').style.display = 'block';
        });
        */
    } else {
        console.error('Bouton customSequenceBtn non trouvé dans le DOM');
    }
});
