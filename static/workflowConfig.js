/**
 * COMMANDS_CONFIG is now loaded dynamically from the backend via /api/get_commands_config
 * See apiService.js for loading logic.
 */

/**
 * SEQUENCE_PRESETS - Predefined sequences for common workflows
 */
export const SEQUENCE_PRESETS = {
    "workflow_complet": {
        name: "Workflow Complet (0-4)",
        steps: ["preparation_dezip", "scene_cut", "analyze_audio", "tracking", "minify_json"],
        description: "Exécute toutes les étapes principales dans l'ordre"
    },
    "analyse_audio_video": {
        name: "Analyse Audio/Vidéo",
        steps: ["scene_cut", "analyze_audio"],
        description: "Découpe les scènes et analyse l'audio uniquement"
    },
    "preparation_tracking": {
        name: "Préparation + Tracking",
        steps: ["preparation_dezip", "tracking"],
        description: "Décompresse les fichiers et lance le tracking"
    }
};

/**
 * SEQUENCE_VALIDATORS - Validation rules for sequences
 */
export const SEQUENCE_VALIDATORS = {
    /**
     * Validates dependencies between steps
     * @param {Array} steps - Array of step keys in execution order
     * @returns {Object} - Validation result with status and message
     */
    validateDependencies(steps) {
        // Check if minify_json comes after tracking/analyze_audio
        const minifyIndex = steps.indexOf("minify_json");
        const trackingIndex = steps.indexOf("tracking");
        const audioIndex = steps.indexOf("analyze_audio");

        if (minifyIndex !== -1) {
            if (trackingIndex === -1 && audioIndex === -1) {
                return {
                    valid: false,
                    message: "La minification JSON requiert l'analyse audio ou le tracking"
                };
            }
            if ((trackingIndex !== -1 && minifyIndex < trackingIndex) || 
                (audioIndex !== -1 && minifyIndex < audioIndex)) {
                return {
                    valid: false,
                    message: "La minification JSON doit être exécutée après l'analyse audio et le tracking"
                };
            }
        }

        // Check if scene_cut comes before analyze_audio (recommended)
        if (audioIndex !== -1 && trackingIndex !== -1) {
            const sceneIndex = steps.indexOf("scene_cut");
            if (sceneIndex === -1) {
                return {
                    valid: true,
                    warning: "Il est recommandé d'exécuter la détection de scènes avant l'analyse audio"
                };
            }
        }

        return { valid: true };
    },

    /**
     * Validates GPU resource allocation
     * @param {Array} steps - Array of step keys in execution order
     * @param {Object} commandsConfig - (optionnel) Config des commandes (sinon récupéré via store)
     * @returns {Object} - Validation result
     */
    validateGpuResources: function(steps, commandsConfig) {
        if (!steps || steps.length === 0) {
            return { valid: false, error: "Aucune étape sélectionnée" };
        }
        
        if (!commandsConfig) {
            return { valid: true, warning: "Impossible de valider les ressources GPU (config manquante)" };
        }
        
        // Vérifier si plusieurs étapes GPU sont présentes
        const gpuSteps = steps.filter(step => commandsConfig[step] && commandsConfig[step].gpu_intensive);
        
        if (gpuSteps.length > 1) {
            return {
                valid: false,
                error: `Plusieurs étapes GPU détectées (${gpuSteps.join(', ')}). Exécution séquentielle requise.`
            };
        }
        
        return { valid: true };
    }
};

// Ce fichier ne contient plus de configuration d'étapes. Utilisez l'API backend et le store pour l'état global.
