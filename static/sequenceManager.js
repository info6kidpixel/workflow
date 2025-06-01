import { notifications } from './notifications.js';
import { animations } from './animations.js';
import store from './store.js';

// import { COMMANDS_CONFIG, SEQUENCE_PRESETS, SEQUENCE_VALIDATORS } from './workflowConfig.js';
import { SEQUENCE_PRESETS, SEQUENCE_VALIDATORS } from './workflowConfig.js';
export { SEQUENCE_PRESETS };

// Variables pour le drag & drop
let draggedItem = null;
let draggingOverItem = null;

/**
 * Lance une séquence personnalisée avec les étapes sélectionnées
 * @param {Array} steps - Liste des clés d'étapes à exécuter
 * @returns {Promise<Object>} - Résultat de l'opération
 */
// NOTE : Cette fonction est redondante avec apiService.js/runCustomSequence et ne doit plus être utilisée directement.
// Pour lancer une séquence, importer et utiliser runCustomSequence de apiService.js.
// export async function runCustomSequence(steps) { ... }
// (Fonction conservée pour référence, mais non exportée)
/* export async function runCustomSequence(steps) {
    try {
        const response = await fetch('/run_custom_sequence', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ steps: steps })
        });
        
        const data = await response.json();
        if (response.ok) {
            notifications.success('Séquence personnalisée lancée avec succès');
            
            // Mettre à jour visuellement les étapes sélectionnées
            steps.forEach(stepKey => {
                const stepElement = document.querySelector(`[data-step-key="${stepKey}"]`);
                if (stepElement) {
                    const statusText = stepElement.querySelector('.status-text');
                    if (statusText) statusText.textContent = 'En attente...';
                    
                    const progressBar = stepElement.querySelector('.progress-bar');
                    if (progressBar) progressBar.style.width = '0%';
                    
                    stepElement.classList.remove('status-idle', 'status-completed', 'status-failed');
                    stepElement.classList.add('status-initiated');
                    
                    const runButton = stepElement.querySelector('.run-button');
                    if (runButton) runButton.disabled = true;
                }
            });
        } else {
            notifications.error(data.message || 'Erreur lors du lancement de la séquence');
        }
        return { success: response.ok, data };
    } catch (error) {
        notifications.error('Erreur lors du lancement de la séquence');
        console.error('Erreur:', error);
        return { success: false, error };
    }
} */

/**
 * Gère les logs d'une étape de séquence
 * Cette fonction est appelée par apiService.js
 */
export function handleSequenceStepLogs(stepKey, logs) {
    // Implémentation à ajouter si nécessaire
    console.log(`Logs pour l'étape ${stepKey} mis à jour`);
}

// Gestionnaires d'événements pour le drag & drop
function handleDragStart(e) {
    draggedItem = e.target;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.innerHTML);
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    draggedItem = null;
    
    // Mettre à jour les numéros des étapes
    updateStepNumbers();
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const item = e.target.closest('.step-selection-item');
    if (item && item !== draggedItem) {
        const container = item.parentElement;
        const afterElement = getDragAfterElement(container, e.clientY);
        
        if (afterElement) {
            container.insertBefore(draggedItem, afterElement);
        } else {
            container.appendChild(draggedItem);
        }
    }
}

function handleDrop(e) {
    e.preventDefault();
    const item = e.target.closest('.step-selection-item');
    if (item && draggedItem) {
        // Mettre à jour l'ordre
        const container = item.parentElement;
        if (draggedItem !== item) {
            const afterElement = getDragAfterElement(container, e.clientY);
            if (afterElement) {
                container.insertBefore(draggedItem, afterElement);
            } else {
                container.appendChild(draggedItem);
            }
        }
    }
    draggedItem = null;
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.step-selection-item:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

/**
 * Initialise la séquence personnalisée dans la modale
 * @param {Object} commandsConfig - La configuration des commandes chargée dynamiquement
 */
export function initCustomSequence() {
    const commandsConfig = store.getState().commandsConfig;

    console.log('Initialisation de la séquence personnalisée...');
    const container = document.getElementById('stepsSelectionContainer');
    if (!container) {
        console.error('Container des étapes non trouvé');
        return;
    }

    // Vider le conteneur
    container.innerHTML = '';

    // Ajouter les presets
    const presetsDiv = document.createElement('div');
    presetsDiv.className = 'sequence-presets';
    presetsDiv.innerHTML = `
        <h3><i class="fas fa-star"></i> Séquences Prédéfinies</h3>
        <div class="preset-buttons">
            ${Object.entries(SEQUENCE_PRESETS).map(([key, preset]) => `
                <button class="preset-button" data-preset="${key}" title="${preset.description}">
                    <i class="fas fa-play-circle"></i>
                    ${preset.name}
                </button>
            `).join('')}
        </div>
    `;
    container.appendChild(presetsDiv);

    // Ajouter un séparateur
    const separator = document.createElement('div');
    separator.className = 'sequence-separator';
    separator.innerHTML = '<span>ou créez une séquence personnalisée</span>';
    container.appendChild(separator);

    // Créer les éléments pour chaque étape
    const stepsDiv = document.createElement('div');
    stepsDiv.className = 'sequence-steps';
    
    Object.entries(commandsConfig).forEach(([key, config], index) => {
        const stepDiv = document.createElement('div');
        stepDiv.className = 'step-selection-item';
        stepDiv.draggable = true;
        stepDiv.dataset.stepKey = key;

        stepDiv.innerHTML = `
            <div class="step-content">
                <input type="checkbox" id="step_${key}" value="${key}">
                <span class="step-number">${index + 1}</span>
                <label for="step_${key}">
                    <i class="${config.icon}"></i>
                    ${config.display_name}
                    ${config.gpu_intensive ? `
                    <div class="gpu-status-badge" title="Cette étape utilise le GPU">
                        <span class="gpu-label">
                            <i class="fas fa-microchip"></i> GPU
                        </span>
                    </div>` : ''}
                </label>
                <span class="step-description">${config.description}</span>
            </div>
            <span class="drag-handle" title="Glisser pour réorganiser"><i class="fas fa-grip-vertical"></i></span>
        `;

        // Ajouter les gestionnaires d'événements pour le drag & drop
        stepDiv.addEventListener('dragstart', handleDragStart);
        stepDiv.addEventListener('dragend', handleDragEnd);
        stepDiv.addEventListener('dragover', handleDragOver);
        stepDiv.addEventListener('drop', handleDrop);

        // Ajouter un effet de survol
        stepDiv.addEventListener('mouseover', () => {
            stepDiv.classList.add('hover');
        });
        
        stepDiv.addEventListener('mouseout', () => {
            stepDiv.classList.remove('hover');
        });

        stepsDiv.appendChild(stepDiv);
    });

    container.appendChild(stepsDiv);

    // Gestionnaire pour la sélection multiple avec Shift
    let lastChecked = null;
    container.addEventListener('click', (e) => {
        const checkbox = e.target.closest('input[type="checkbox"]');
        if (!checkbox) return;

        if (e.shiftKey && lastChecked) {
            const checkboxes = Array.from(container.querySelectorAll('input[type="checkbox"]'));
            const start = checkboxes.indexOf(checkbox);
            const end = checkboxes.indexOf(lastChecked);
            
            checkboxes
                .slice(Math.min(start, end), Math.max(start, end) + 1)
                .forEach(cb => cb.checked = lastChecked.checked);
        }
        
        lastChecked = checkbox;
    });

    // Ajouter la validation de séquence
    const startButton = document.getElementById('startCustomSequenceBtn');
    if (startButton) {
        startButton.addEventListener('click', () => {
            const selectedSteps = [];
            container.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                selectedSteps.push(checkbox.value);
            });

            if (selectedSteps.length === 0) {
                notifications.warning('Veuillez sélectionner au moins une étape.');
                animations.shake(startButton);
                return;
            }

            // Valider la séquence
            const validation = SEQUENCE_VALIDATORS.validateSequence(selectedSteps);
            if (!validation.valid) {
                notifications.error(validation.message);
                animations.shake(startButton);
                return;
            }

            // La validation est gérée par eventHandlers.js pour le lancement effectif
        });
    }

    console.log('Initialisation terminée');
}

function updateStepNumbers() {
    document.querySelectorAll('.sequence-steps .step-selection-item').forEach((item, index) => {
        const numberSpan = item.querySelector('.step-number');
        if (numberSpan) {
            numberSpan.textContent = index + 1;
            // Ajouter une animation subtile
            item.classList.add('reordering');
            setTimeout(() => item.classList.remove('reordering'), 300);
        }
    });
}

// Pour accéder à la config dynamique :
// const commandsConfig = store.getState().commandsConfig;
// Pour accéder à l'état processInfo :
// const processInfo = store.getState().processInfo;
