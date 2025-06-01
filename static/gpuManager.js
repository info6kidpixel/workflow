import { GPU_STATES, GPU_STATUS_MESSAGES } from './constants.js';
import { notifications } from './notifications.js';
import { gpuElements } from './domElements.js';

class GpuManager {
    constructor() {
        this.currentUser = null;
        this.waitingSteps = new Set();
        this.gpuIntensiveSteps = new Set();
        this.lastUpdateTime = null;
    }

    async isGpuAvailable() {
        try {
            const response = await fetch('/api/gpu_status');
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            return data.available;
        } catch (error) {
            console.error('Erreur lors de la vérification du statut GPU:', error);
            return false;
        }
    }

    handleGpuStatusUpdate(stepElement, stepData) {
        if (!stepData.gpu_intensive) return;

        const stepKey = stepElement.dataset.stepKey;
        
        // Gestion des étapes en attente
        if (stepData.status === 'pending_gpu') {
            if (!this.waitingSteps.has(stepKey)) {
                this.waitingSteps.add(stepKey);
            }
        } else {
            this.waitingSteps.delete(stepKey);
        }

        // Mise à jour de l'utilisateur actuel du GPU
        const oldUser = this.currentUser;
        if (stepData.status === 'running') {
            this.currentUser = stepKey;
            if (oldUser !== stepKey) {
                this.updateGpuInfoPanel();
            }
        } else if (this.currentUser === stepKey && ['completed', 'failed', 'cancelled'].includes(stepData.status)) {
            this.currentUser = null;
            this.updateGpuInfoPanel();
        }

        this.lastUpdateTime = Date.now();
    }

    getGpuStatusClass(status) {
        if (status === 'available') return 'available';
        if (status === 'in_use') return 'in-use';
        if (status.startsWith('blocked_by_')) return 'waiting';
        if (status === 'error') return 'error';
        return 'unknown';
    }

    getGpuStatusIcon(status) {
        if (status === 'available') return 'fa-check-circle';
        if (status === 'in_use') return 'fa-running';
        if (status.startsWith('blocked_by_')) return 'fa-clock';
        if (status === 'error') return 'fa-exclamation-triangle';
        return 'fa-question-circle';
    }

    getGpuStatusText(gpuStatus, stepKey) {
        if (!gpuStatus) return '';
        if (gpuStatus.startsWith('blocked_by_')) {
            const blockingStep = gpuStatus.split('blocked_by_')[1];
            return `En attente du GPU (utilisé par ${blockingStep})`;
        }
        return GPU_STATUS_MESSAGES[gpuStatus] || gpuStatus;
    }

    getGpuBadgeDetails(gpuStatus, gpuIntensive) {
        if (!gpuIntensive) {
            return null;
        }

        let className = 'gpu-status';
        let icon = 'fa-microchip';
        let text = '';

        if (gpuStatus) {
            className += ' ' + this.getGpuStatusClass(gpuStatus);
            icon = this.getGpuStatusIcon(gpuStatus);
            text = this.getGpuStatusText(gpuStatus);
        }

        return {
            className,
            icon,
            text,
            shouldPulse: gpuStatus === 'waiting' || gpuStatus?.startsWith('blocked_by_')
        };
    }

    updateGpuInfoPanel() {
        if (!gpuElements.gpuInfoPanel) return;

        const gpuStatusData = {
            currentUser: this.currentUser,
            waitingCount: this.waitingSteps.size,
            isAvailable: !this.currentUser,
        };

        // Update current status class and text
        const statusClass = gpuStatusData.isAvailable ? 'available' : 'in-use';
        const statusText = gpuStatusData.isAvailable ? 'Disponible' : 'En utilisation';
        const statusIcon = gpuStatusData.isAvailable ? 'fa-check-circle' : 'fa-running';
        
        if (gpuElements.currentGpuStatus) {
            gpuElements.currentGpuStatus.className = `gpu-status ${statusClass}`;
            gpuElements.currentGpuStatus.innerHTML = `<i class="fas ${statusIcon}"></i> ${statusText}`;
        }

        // Update current user
        if (gpuElements.currentGpuUser) {
            if (gpuStatusData.currentUser) {
                gpuElements.currentGpuUser.textContent = PROCESS_INFO_CLIENT[gpuStatusData.currentUser]?.display_name || gpuStatusData.currentUser;
            } else {
                gpuElements.currentGpuUser.textContent = 'Aucune tâche';
            }
        }

        // Update waiting tasks
        if (gpuElements.gpuWaitingTasks) {
            gpuElements.gpuWaitingTasks.textContent = `${gpuStatusData.waitingCount} tâche(s)`;
            gpuElements.gpuWaitingTasks.className = gpuStatusData.waitingCount > 0 ? 'waiting' : '';
        }
    }
}

export const gpuManager = new GpuManager();