import { animations } from './animations.js';
import { notifications } from './notifications.js';

class InteractionManager {
    constructor() {
        this.initializeTooltips();
        this.initializeRippleEffect();
        this.initializeHoverEffects();
        this.initializeScrollEffects();
        this.initializeSequenceInteractions();
    }

    initializeSequenceInteractions() {
        this.initializePresetButtons();
        this.initializeSequenceDragAndDrop();
        this.initializeSequenceValidation();
    }

    initializeTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(element => {
            let tooltipElement = null;
            
            element.addEventListener('mouseenter', () => {
                tooltipElement = document.createElement('div');
                tooltipElement.className = 'tooltip';
                tooltipElement.textContent = element.dataset.tooltip;
                document.body.appendChild(tooltipElement);
                
                const rect = element.getBoundingClientRect();
                const tooltipRect = tooltipElement.getBoundingClientRect();
                
                tooltipElement.style.top = rect.top - tooltipRect.height - 10 + 'px';
                tooltipElement.style.left = rect.left + (rect.width - tooltipRect.width) / 2 + 'px';
                
                animations.fadeIn(tooltipElement, 200);
            });
            
            element.addEventListener('mouseleave', () => {
                if (tooltipElement) {
                    animations.fadeOut(tooltipElement, 200).then(() => {
                        tooltipElement.remove();
                        tooltipElement = null;
                    });
                }
            });
        });
    }

    initializeRippleEffect() {
        document.querySelectorAll('.action-button, .run-button, .cancel-button').forEach(button => {
            button.addEventListener('click', e => {
                const ripple = document.createElement('div');
                ripple.className = 'ripple';
                button.appendChild(ripple);
                
                const rect = button.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                ripple.style.width = ripple.style.height = size + 'px';
                
                const x = e.clientX - rect.left - size / 2;
                const y = e.clientY - rect.top - size / 2;
                ripple.style.left = x + 'px';
                ripple.style.top = y + 'px';
                
                setTimeout(() => ripple.remove(), 600);
            });
        });
    }

    initializeHoverEffects() {
        document.querySelectorAll('.step').forEach(step => {
            step.addEventListener('mouseenter', () => {
                step.style.transform = 'translateY(-5px)';
                step.style.boxShadow = '0 8px 16px rgba(0,0,0,0.3)';
            });
            
            step.addEventListener('mouseleave', () => {
                step.style.transform = 'translateY(0)';
                step.style.boxShadow = '';
            });
        });
    }

    initializeScrollEffects() {
        const scrollToTop = document.createElement('button');
        scrollToTop.className = 'scroll-to-top';
        scrollToTop.innerHTML = '<i class="fas fa-arrow-up"></i>';
        document.body.appendChild(scrollToTop);
        
        window.addEventListener('scroll', () => {
            if (window.pageYOffset > 300) {
                scrollToTop.style.display = 'block';
                animations.fadeIn(scrollToTop, 300);
            } else {
                animations.fadeOut(scrollToTop, 300);
            }
        });
        
        scrollToTop.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    showLoadingSpinner(element, text = 'Chargement...') {
        const spinner = document.createElement('div');
        spinner.className = 'loading-spinner';
        spinner.innerHTML = `
            <div class="spinner"></div>
            <span>${text}</span>
        `;
        
        element.appendChild(spinner);
        animations.fadeIn(spinner);
        
        return {
            hide: () => {
                animations.fadeOut(spinner).then(() => spinner.remove());
            },
            updateText: (newText) => {
                spinner.querySelector('span').textContent = newText;
            }
        };
    }

    confirmDialog(options) {
        return new Promise((resolve) => {
            const dialog = document.createElement('div');
            dialog.className = 'confirm-dialog';
            dialog.innerHTML = `
                <div class="confirm-dialog-content">
                    <h3>
                        <i class="fas fa-question-circle"></i>
                        ${options.title || 'Confirmation'}
                    </h3>
                    <p>${options.message}</p>
                    <div class="confirm-dialog-buttons">
                        <button class="confirm-yes">
                            <i class="fas fa-check"></i>
                            ${options.confirmText || 'Confirmer'}
                        </button>
                        <button class="confirm-no">
                            <i class="fas fa-times"></i>
                            ${options.cancelText || 'Annuler'}
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(dialog);
            animations.fadeIn(dialog);
            
            const close = (result) => {
                animations.fadeOut(dialog).then(() => {
                    dialog.remove();
                    resolve(result);
                });
            };
            
            dialog.querySelector('.confirm-yes').addEventListener('click', () => close(true));
            dialog.querySelector('.confirm-no').addEventListener('click', () => close(false));
        });
    }
    initializePresetButtons() {
        document.querySelectorAll('.preset-button').forEach(button => {
            button.addEventListener('click', () => {
                const presetKey = button.dataset.preset;
                this.applyPresetSequence(presetKey);
            });
        });
    }

    initializeSequenceDragAndDrop() {
        const container = document.getElementById('stepsSelectionContainer');
        if (!container) return;

        let draggedItem = null;

        container.addEventListener('dragover', e => {
            e.preventDefault();
            const afterElement = this.getDragAfterElement(container, e.clientY);
            const draggable = document.querySelector('.dragging');
            
            if (afterElement) {
                container.insertBefore(draggable, afterElement);
            } else {
                container.appendChild(draggable);
            }
        });

        document.querySelectorAll('.step-selection-item').forEach(item => {
            item.addEventListener('dragstart', () => {
                item.classList.add('dragging');
                draggedItem = item;
            });

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
                draggedItem = null;
                this.updateStepNumbers();
            });

            // Touch support
            item.addEventListener('touchstart', e => {
                draggedItem = item;
                item.classList.add('dragging');
                const touch = e.touches[0];
                const offsetY = touch.clientY - item.getBoundingClientRect().top;
                
                const moveHandler = e => {
                    e.preventDefault();
                    const touch = e.touches[0];
                    item.style.position = 'absolute';
                    item.style.top = touch.clientY - offsetY + 'px';
                    
                    const afterElement = this.getDragAfterElement(container, touch.clientY);
                    if (afterElement) {
                        container.insertBefore(item, afterElement);
                    } else {
                        container.appendChild(item);
                    }
                };
                
                const endHandler = () => {
                    item.removeEventListener('touchmove', moveHandler);
                    item.removeEventListener('touchend', endHandler);
                    item.classList.remove('dragging');
                    item.style.position = '';
                    item.style.top = '';
                    draggedItem = null;
                    this.updateStepNumbers();
                };
                
                item.addEventListener('touchmove', moveHandler);
                item.addEventListener('touchend', endHandler);
            });
        });
    }

    getDragAfterElement(container, y) {
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

    updateStepNumbers() {
        const items = document.querySelectorAll('.step-selection-item');
        items.forEach((item, index) => {
            const numberSpan = item.querySelector('.step-number');
            if (numberSpan) {
                numberSpan.textContent = index + 1;
                item.classList.add('reordering');
                setTimeout(() => item.classList.remove('reordering'), 300);
            }
        });
    }

    initializeSequenceValidation() {
        const startButton = document.getElementById('startCustomSequenceBtn');
        if (!startButton) return;

        startButton.addEventListener('click', () => {
            const selectedItems = [...document.querySelectorAll('.step-selection-item input[type="checkbox"]:checked')]
                .map(checkbox => checkbox.closest('.step-selection-item'))
                .filter(item => item);

            if (selectedItems.length === 0) {
                notifications.warning('Veuillez sélectionner au moins une étape.');
                return;
            }

            const sequence = selectedItems.map(item => item.dataset.stepKey);
            this.validateAndExecuteSequence(sequence);
        });
    }

    async validateAndExecuteSequence(sequence) {
        const errorLogger = (await import('./errorLogger.js')).errorLogger;
        const validation = errorLogger.validateSequence(sequence);

        if (!validation.valid) {
            return;
        }

        // Si tout est valide, on peut fermer la modale et lancer la séquence
        const modal = document.getElementById('customSequenceModal');
        if (modal) {
            animations.fadeOut(modal).then(() => {
                modal.style.display = 'none';
                this.executeSequence(sequence);
            });
        }
    }

    async executeSequence(sequence) {
        // Correction : utiliser apiService.js
        const { runCustomSequence } = await import('./apiService.js');
        await runCustomSequence(sequence);
    }

    applyPresetSequence(presetKey) {
        const { SEQUENCE_PRESETS } = import('./workflowConfig.js');
        const preset = SEQUENCE_PRESETS[presetKey];
        
        if (!preset) return;

        // Décocher toutes les cases
        document.querySelectorAll('.step-selection-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        // Cocher les étapes du preset
        preset.steps.forEach(stepKey => {
            const checkbox = document.querySelector(`input[id="step_${stepKey}"]`);
            if (checkbox) {
                checkbox.checked = true;
                const item = checkbox.closest('.step-selection-item');
                if (item) {
                    item.classList.add('reordering');
                    setTimeout(() => item.classList.remove('reordering'), 300);
                }
            }
        });

        notifications.info(`Preset "${preset.name}" appliqué`);
    }
}

export const interactions = new InteractionManager();
