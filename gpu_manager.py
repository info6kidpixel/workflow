"""
GPU Manager - Module qui gère l'accès et l'allocation du GPU.

Ce module encapsule la logique de gestion du GPU dans une classe GPUManager pour:
1. Réduire les variables globales
2. Centraliser la logique
3. Simplifier le code principal
"""
import contextlib
import time
import logging
import threading
from typing import Optional, List, Tuple, Dict, Any, Callable

class GpuUnavailableError(Exception):
    """Exception personnalisée pour GPU non disponible."""
    pass

class GPUManager:
    """
    Gestionnaire de ressources GPU centralisé.
    Gère l'allocation du GPU, les attentes, et les files d'attente.
    """
    
    def __init__(self, logger: logging.Logger, wait_timeout: int = 300):
        """
        Initialise le gestionnaire GPU.
        
        Args:
            logger: Logger pour les messages
            wait_timeout: Délai maximum d'attente pour le GPU en secondes
        """
        self._logger = logger
        self._wait_timeout = wait_timeout
        self._gpu_in_use_by = None
        self._gpu_lock = threading.Lock()
        self._gpu_waiting_queue = []
        self._app_stop_event = threading.Event()
    
    def set_app_stop_event(self, event: threading.Event) -> None:
        """Définit l'événement d'arrêt de l'application pour les attentes interruptibles."""
        self._app_stop_event = event
    
    def set_commands_config(self, commands_config: Dict[str, Dict[str, Any]]) -> None:
        """
        Définit la configuration des commandes pour vérifier les tâches GPU intensives.
        
        Args:
            commands_config: Configuration des commandes avec les métadonnées
        """
        self._commands_config = commands_config
    
    @property
    def current_user(self) -> Optional[str]:
        """Retourne l'utilisateur actuel du GPU ou None s'il est libre."""
        with self._gpu_lock:
            return self._gpu_in_use_by
    
    @contextlib.contextmanager
    def gpu_session(self, step_key: str, wait_if_busy: bool = False):
        """
        Context manager pour acquérir et libérer le GPU.
        
        Args:
            step_key: Clé de l'étape qui veut utiliser le GPU
            wait_if_busy: Si True, attend jusqu'à wait_timeout que le GPU se libère
            
        Raises:
            GpuUnavailableError: Si le GPU ne peut être acquis
        """
        acquired = False
        wait_start_time = None
        
        # Valider que c'est une tâche GPU valide
        is_gpu_intensive_task = self._commands_config.get(step_key, {}).get("gpu_intensive", False)
        if not is_gpu_intensive_task:
            yield  # Les tâches non-GPU passent directement
            return

        try:
            wait_start_time = time.time()
            while True:
                with self._gpu_lock:
                    if self._gpu_in_use_by is None:
                        self._gpu_in_use_by = step_key
                        self._logger.info(f"GPU alloué à l'étape '{step_key}'")
                        acquired = True
                        break
                    elif self._gpu_in_use_by == step_key:
                        self._logger.debug(f"GPU: '{step_key}' possède déjà le GPU")
                        acquired = True
                        break
                    elif not wait_if_busy:
                        msg = f"GPU occupé par '{self._gpu_in_use_by}'"
                        self._logger.warning(f"GPU: {msg}, '{step_key}' ne peut pas démarrer.")
                        raise GpuUnavailableError(msg)
                    elif step_key not in self._gpu_waiting_queue:
                        # Ajout à la file d'attente pour suivi
                        self._gpu_waiting_queue.append(step_key)
                        self._logger.info(f"GPU: '{step_key}' ajouté à la file d'attente GPU (position {len(self._gpu_waiting_queue)})")

                # Si on arrive ici, c'est qu'on attend le GPU
                # Vérifier le timeout si on attend
                if wait_if_busy:
                    wait_duration = time.time() - wait_start_time
                    if wait_duration > self._wait_timeout:
                        msg = f"Timeout d'attente GPU pour '{step_key}' après {self._wait_timeout}s"
                        self._logger.error(f"GPU: {msg}")
                        
                        # Retirer de la file d'attente
                        with self._gpu_lock:
                            if step_key in self._gpu_waiting_queue:
                                self._gpu_waiting_queue.remove(step_key)
                                self._logger.info(f"GPU: '{step_key}' retiré de la file d'attente après timeout")
                                
                        raise GpuUnavailableError(msg)
                    
                    self._logger.debug(f"GPU: '{step_key}' attend le GPU (occupé par '{self._gpu_in_use_by}', {wait_duration:.1f}s)...")
                    
                    # Attente interruptible - réduire le temps d'attente pour vérifier le timeout plus fréquemment
                    if self._app_stop_event.wait(0.1):  # Attendre 0.1s au lieu de 5s pour vérifier le timeout plus souvent
                        with self._gpu_lock:
                            if step_key in self._gpu_waiting_queue:
                                self._gpu_waiting_queue.remove(step_key)
                        raise GpuUnavailableError(f"Arrêt de l'application pendant l'attente du GPU pour {step_key}")

            yield  # Exécution du bloc with

        except Exception as e:
            if not isinstance(e, GpuUnavailableError):
                self._logger.error(f"GPU: Erreur inattendue pour '{step_key}': {e}", exc_info=True)
            
            # Nettoyage en cas d'erreur
            with self._gpu_lock:
                if step_key in self._gpu_waiting_queue:
                    self._gpu_waiting_queue.remove(step_key)
                    
            raise  # Propager l'erreur

        finally:
            if acquired and is_gpu_intensive_task:
                with self._gpu_lock:
                    if self._gpu_in_use_by == step_key:
                        self._gpu_in_use_by = None
                        wait_duration = time.time() - wait_start_time if wait_start_time else 0
                        self._logger.info(f"GPU libéré par '{step_key}' (durée attente: {wait_duration:.1f}s)")
                        
                        # Retirer de la file d'attente si présent
                        if step_key in self._gpu_waiting_queue:
                            self._gpu_waiting_queue.remove(step_key)
                        
                        # Lancer la prochaine tâche en attente s'il y en a
                        threading.Thread(target=self.launch_pending_task, daemon=True).start()
                    else:
                        self._logger.warning(f"GPU: Incohérence - '{step_key}' essaie de libérer le GPU possédé par '{self._gpu_in_use_by}'")

    def can_run_gpu_task(self, step_key: str, wait_if_busy: bool = False) -> bool:
        """
        Vérifie si une tâche GPU peut s'exécuter.
        
        Args:
            step_key: Clé de l'étape qui veut utiliser le GPU
            wait_if_busy: Si True, attend jusqu'à wait_timeout que le GPU se libère
            
        Returns:
            bool: True si le GPU est disponible ou si l'étape l'utilise déjà
        """
        if not self._commands_config.get(step_key, {}).get("gpu_intensive", False):
            return True

        # Check simple sans acquérir le GPU
        with self._gpu_lock:
            if self._gpu_in_use_by is None or self._gpu_in_use_by == step_key:
                return True
            elif not wait_if_busy:
                return False
        
        # Si wait_if_busy=True et le GPU est occupé par un autre:
        # Plutôt que d'acquérir le GPU juste pour vérifier,
        # on indique que la tâche doit attendre (puisque can_run_gpu_task est
        # souvent appelé avant gpu_session)
        return False

    def release_gpu(self, step_key: str) -> bool:
        """
        Libère le GPU pour une étape donnée.
        
        Args:
            step_key: Clé de l'étape qui libère le GPU
            
        Returns:
            bool: True si le GPU a été libéré, False sinon
        """
        with self._gpu_lock:
            if self._gpu_in_use_by == step_key:
                self._gpu_in_use_by = None
                self._logger.info(f"GPU libéré (via release_gpu explicite) par l'étape '{step_key}'")
                return True
            return False

    def get_waiting_tasks(self) -> List[str]:
        """
        Retourne la liste des tâches en attente du GPU.
        
        Returns:
            List[str]: Liste des clés des étapes en attente
        """
        with self._gpu_lock:
            return self._gpu_waiting_queue.copy()
    
    def set_launch_pending_task_callback(self, callback: Callable[[], None]) -> None:
        """
        Définit la callback à appeler quand le GPU est libéré pour lancer 
        une tâche en attente. La callback est responsable de la logique métier.
        
        Args:
            callback: Fonction à appeler sans arguments
        """
        self._launch_pending_task_callback = callback
        
    def launch_pending_task(self) -> None:
        """Lance la prochaine tâche GPU en attente dans la file d'attente."""
        self._logger.info(f"DEBUG: launch_pending_task called. GPU in use: {self._gpu_in_use_by}, Queue: {self._gpu_waiting_queue}")
        
        if self._app_stop_event and self._app_stop_event.is_set():
            self._logger.debug("GPU: Application en cours d'arrêt, pas de lancement de tâche en attente")
            return

        with self._gpu_lock:
            self._logger.info(f"DEBUG: In launch_pending_task lock. GPU in use: {self._gpu_in_use_by}, Queue: {self._gpu_waiting_queue}")
            if self._gpu_in_use_by is not None:
                self._logger.debug(f"GPU: GPU déjà utilisé par '{self._gpu_in_use_by}', pas de lancement de tâche en attente")
                return
            if not self._gpu_waiting_queue:
                self._logger.debug("GPU: File d'attente vide, pas de lancement.")
                return
            next_task_key = self._gpu_waiting_queue[0]
            self._logger.info(f"GPU: Tentative de lancement de la tâche en attente '{next_task_key}'")

        if hasattr(self, '_launch_pending_task_callback') and self._launch_pending_task_callback:
            try:
                self._logger.info(f"DEBUG: Calling _launch_pending_task_callback for {next_task_key}")
                threading.Thread(target=self._launch_pending_task_callback, daemon=True).start()
            except Exception as e:
                self._logger.error(f"GPU: Erreur lors du lancement du thread pour _launch_pending_task_callback: {e}", exc_info=True)
        else:
            self._logger.warning("GPU: _launch_pending_task_callback non définie.")

    def _launch_pending_task_callback(self):
        """
        Callback appelée quand le GPU est libéré pour lancer la prochaine tâche en attente.
        Cette méthode est vide par défaut et doit être remplacée par l'appelant.
        """
        if self._launch_pending_task_callback:
            try:
                self._launch_pending_task_callback()
            except Exception as e:
                self._logger.error(f"GPU: Erreur dans la callback de lancement de tâche: {e}", exc_info=True)

# Export explicite pour éviter tout problème d'import
__all__ = ["GPUManager", "GpuUnavailableError"]
