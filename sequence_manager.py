import threading
import time

class SequenceManager:
    def __init__(self, process_manager, logger):
        self.logger = logger
        self.is_currently_running_any_sequence = False
        self.sequence_lock = threading.Lock()
        self.last_sequence_outcome = {"status": "never_run", "timestamp": None}
        self.process_manager = process_manager
        self.current_auto_mode_active_step_key = None
        self.stop_requested = False

    def is_running(self):
        return self.is_currently_running_any_sequence

    def get_last_sequence_type(self):
        return self.last_sequence_outcome.get('type', 'Unknown')

    def get_current_auto_mode_key(self):
        return self.current_auto_mode_active_step_key

    def set_current_auto_mode_key(self, key):
        self.current_auto_mode_active_step_key = key

    def lock(self):
        return self.sequence_lock

    def set_running(self, value: bool):
        self.is_currently_running_any_sequence = value

    def get_last_outcome(self):
        return self.last_sequence_outcome

    def set_last_outcome(self, outcome):
        self.last_sequence_outcome = outcome

    def update_last_sequence_outcome(self, status, message):
        self.set_last_outcome({
            "status": status,
            "type": self.current_sequence_type,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "message": message
        })

    def execute_sequence_worker(self, steps, sequence_type="Manual"):
        """
        Exécute une séquence d'étapes dans un thread séparé

        Args:
            steps (list): Liste des clés d'étapes à exécuter
            sequence_type (str): Type de séquence ("Manual" ou "AutoMode")
        
        Returns:
            bool: True si la séquence s'est terminée avec succès, False sinon
        """
        with self.sequence_lock:
            self.is_currently_running_sequence = True
            self.current_sequence_steps = steps
            self.current_sequence_type = sequence_type
            
            try:
                self.logger.info(f"Démarrage de la séquence {sequence_type}: {', '.join(steps)}")
                
                for step_key in steps:
                    if self.stop_requested:
                        self.logger.info(f"Séquence {sequence_type} arrêtée sur demande")
                        self.update_last_sequence_outcome("canceled", f"Séquence arrêtée manuellement à l'étape {step_key}")
                        return False  # Retourne False en cas d'annulation
                    
                    self.logger.info(f"Exécution de l'étape {step_key}")
                    
                    if sequence_type == "AutoMode":
                        self.set_current_auto_mode_key(step_key)
                    
                    # Lancer le processus
                    self.process_manager.run_process_async(step_key, is_auto_mode_step=(sequence_type == "AutoMode"), sequence_type=sequence_type)
                    
                    # Attendre la fin du processus avec un Event plutôt qu'un polling
                    info = self.process_manager.process_info[step_key]
                    process_completed = threading.Event()
                    
                    def monitor_process():
                        while True:
                            status = info['status']
                            if status in ('completed', 'failed', 'canceled'):
                                process_completed.set()
                                break
                            time.sleep(0.5)
                    
                    monitor_thread = threading.Thread(target=monitor_process)
                    monitor_thread.daemon = True
                    monitor_thread.start()
                    
                    # Attendre la fin du processus ou l'arrêt demandé
                    while not process_completed.is_set() and not self.stop_requested:
                        process_completed.wait(1)
                    
                    if self.stop_requested:
                        self.process_manager.cancel_step(step_key)
                        self.logger.info(f"Séquence {sequence_type} arrêtée sur demande")
                        self.update_last_sequence_outcome("canceled", f"Séquence arrêtée manuellement à l'étape {step_key}")
                        return False  # Retourne False en cas d'annulation
                    
                    if info['status'] == 'failed':
                        self.logger.error(f"Étape {step_key} échouée, arrêt de la séquence")
                        self.update_last_sequence_outcome("failed", f"Échec à l'étape {step_key}")
                        return False  # Retourne False en cas d'échec
                
                # Si toutes les étapes sont terminées avec succès
                if not self.stop_requested and all(self.process_manager.process_info[step]['status'] == 'completed' for step in steps):
                    self.logger.info(f"Séquence {sequence_type} terminée avec succès")
                    self.update_last_sequence_outcome("success", "Toutes les étapes terminées avec succès")
                    return True  # Retourne True en cas de succès
                else:
                    # Si on arrive ici, c'est qu'il y a eu un problème non géré
                    self.update_last_sequence_outcome("failed", "Fin de séquence avec statut incohérent")
                    return False  # Retourne False par défaut
            
            except Exception as e:
                self.logger.error(f"Erreur lors de l'exécution de la séquence {sequence_type}: {e}", exc_info=True)
                self.update_last_sequence_outcome("failed", f"Erreur inattendue: {str(e)}")
                return False  # Retourne False en cas d'exception
            
            finally:
                # Réinitialiser l'état de la séquence
                self.is_currently_running_sequence = False
                self.current_sequence_steps = []
                self.current_sequence_type = None
                self.stop_requested = False
                
                # Réinitialiser la clé auto mode si nécessaire
                if sequence_type == "AutoMode":
                    self.set_current_auto_mode_key(None)
