/**
 * Module pour la journalisation des erreurs côté client
 * Permet d'envoyer les erreurs JavaScript au serveur pour une meilleure traçabilité
 */

import { notifications } from './notifications.js';
import { SEQUENCE_VALIDATORS } from './workflowConfig.js';

class ErrorLogger {
    constructor() {
        this.errorCache = new Map();
        this.sequenceValidationErrors = new Map();
        
        // Intercepter les erreurs non gérées
        window.addEventListener('error', this.handleGlobalError.bind(this));
        
        // Intercepter les rejets de promesses non gérés
        window.addEventListener('unhandledrejection', this.handleUnhandledRejection.bind(this));
        
        console.log('ErrorLogger: Initialized');
    }
    
    /**
     * Gère les erreurs globales non capturées
     */
    handleGlobalError(event) {
        const { message, filename, lineno, colno, error } = event;
        
        this.logError({
            type: 'UNCAUGHT_ERROR',
            message: message,
            stack: error ? error.stack : `Error at ${filename}:${lineno}:${colno}`,
            component: this.extractComponentFromFilename(filename)
        });
        
        // Ne pas empêcher le comportement par défaut du navigateur
        return false;
    }
    
    /**
     * Gère les rejets de promesses non gérés
     */
    handleUnhandledRejection(event) {
        const error = event.reason;
        
        this.logError({
            type: 'UNHANDLED_REJECTION',
            message: error ? (error.message || String(error)) : 'Unknown promise rejection',
            stack: error && error.stack ? error.stack : 'No stack trace available',
            component: 'Promise'
        });
    }
    
    /**
     * Méthode publique pour journaliser manuellement une erreur
     */
    logError(errorData) {
        const { type = 'MANUAL_ERROR', message, stack = 'No stack trace provided', component = 'Unknown' } = errorData;
        
        // Afficher dans la console pour le débogage local
        console.error(`[${type}] ${message}`);
        if (stack) console.debug(stack);
        
        // Envoyer au serveur
        this.sendErrorToServer({
            type,
            message,
            stack,
            component
        });
    }
    
    /**
     * Envoie l'erreur au serveur
     */
    async sendErrorToServer(errorData) {
        try {
            const response = await fetch('/api/log_client_error', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(errorData)
            });
            
            if (!response.ok) {
                console.error('Failed to send error to server:', await response.text());
            }
        } catch (err) {
            // Éviter une boucle infinie si l'envoi d'erreur échoue
            console.error('Error sending error to server:', err);
        }
    }
    
    /**
     * Extrait le nom du composant à partir du nom de fichier
     */
    extractComponentFromFilename(filename) {
        if (!filename) return 'Unknown';
        
        // Extraire le nom du fichier sans le chemin
        const match = filename.match(/([^/\\]+)\.js$/);
        return match ? match[1] : filename;
    }

    /**
     * Valide une séquence et enregistre les erreurs/avertissements
     * @param {Array} steps - Liste des étapes à valider
     * @returns {Object} - Résultat de la validation
     */
    validateSequence(steps) {
        const result = {
            valid: true,
            errors: [],
            warnings: []
        };

        // Valider les dépendances
        const depValidation = SEQUENCE_VALIDATORS.validateDependencies(steps);
        if (!depValidation.valid) {
            result.valid = false;
            result.errors.push({
                type: 'dependency_error',
                message: depValidation.message
            });
        }
        if (depValidation.warning) {
            result.warnings.push({
                type: 'dependency_warning',
                message: depValidation.warning
            });
        }

        // Valider les ressources GPU
        const gpuValidation = SEQUENCE_VALIDATORS.validateGpuResources(steps);
        if (!gpuValidation.valid) {
            result.valid = false;
            result.errors.push({
                type: 'gpu_error',
                message: gpuValidation.message
            });
        }
        if (gpuValidation.warning) {
            result.warnings.push({
                type: 'gpu_warning',
                message: gpuValidation.warning
            });
        }

        // Enregistrer les erreurs pour cette séquence
        const sequenceKey = steps.join('_');
        this.sequenceValidationErrors.set(sequenceKey, result);

        // Afficher les notifications
        if (!result.valid) {
            result.errors.forEach(error => {
                notifications.error(error.message);
            });
        }
        result.warnings.forEach(warning => {
            notifications.warning(warning.message);
        });

        return result;
    }

    /**
     * Récupère les erreurs de validation pour une séquence
     * @param {Array} steps - Liste des étapes
     * @returns {Object|null} - Résultat de la validation ou null
     */
    getSequenceValidationErrors(steps) {
        const sequenceKey = steps.join('_');
        return this.sequenceValidationErrors.get(sequenceKey) || null;
    }
}

// Exporter une instance unique
export const errorLogger = new ErrorLogger();
