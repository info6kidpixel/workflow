import { PROCESS_INFO_CLIENT } from './state.js';
import { gpuManager } from './gpuManager.js';

export function updateGpuInfoPanel() {
    gpuManager.updateGpuInfoPanel();
}

// Fonction pour initialiser le panneau
export function initGpuInfoPanel() {
    // Mise à jour initiale
    updateGpuInfoPanel();
}
