import contextlib
import logging
import subprocess
import threading
import time
import os
from pathlib import Path
from utils import format_duration_seconds
from collections import deque

class ProcessManager:
    def __init__(self, config, logger, gpu_manager=None):
        """
        Initialise le gestionnaire de processus
        
        Args:
            config (dict): Configuration des commandes
            logger (logging.Logger): Logger pour les messages
            gpu_manager (GPUManager, optional): Gestionnaire GPU
        """
        self.config = config
        self._logger = logger
        self.gpu_manager = gpu_manager
        self._initialize_all_process_info()  # Renommé pour clarifier l'intention

    def _initialize_all_process_info(self):
        """Initialize process information dictionary for all steps in the configuration."""
        self.process_info = {}
        for step_key, step_config in self.config.items():
            info = self._create_step_info(step_key, step_config)  # Appel à la méthode renommée
            if info:
                self.process_info[step_key] = info

    def _create_step_info(self, step_key, step_config):
        """Crée le dictionnaire d'information initial pour une seule étape."""
        # Utiliser 'command' ou 'cmd' selon ce qui est disponible dans la configuration
        cmd = step_config.get('command', step_config.get('cmd'))
        if not cmd:
            self._logger.error(f"Configuration invalide pour {step_key}: commande manquante")
            return None
            
        return {
            'cmd': cmd,
            'cwd': step_config.get('cwd'),
            'status': 'idle',
            'log': deque(maxlen=300),
            'return_code': None,
            'process': None,
            'progress_current': 0,
            'progress_total': 0,
            'progress_text': '',
            'start_time': None,
            'end_time': None,
            'duration': None,
            'gpu_intensive': step_config.get('gpu_intensive', False),
            'progress_patterns': step_config.get('progress_patterns', {})
        }

    def get_active_step_key(self, current_auto_mode_key=None):
        if current_auto_mode_key and self.process_info[current_auto_mode_key]['status'] in ['running', 'starting', 'initiated', 'pending_gpu']:
            return current_auto_mode_key
        for k, v in self.process_info.items():
            if v['status'] in ('running', 'pending_gpu', 'starting', 'initiated'):
                return k
        for k, v in self.process_info.items():
            if v['status'] == 'pending_gpu':
                return k
        return None

    def cancel_step(self, step_key, current_auto_mode_key=None):
        # Vérifier d'abord si l'étape existe
        if step_key not in self.process_info:
            self._logger.warning(f"Tentative d'annulation d'une étape inexistante: {step_key}")
            return False, None, f"Étape '{step_key}' non trouvée dans la configuration."
            
        actual_step_to_terminate_key = self.get_active_step_key(current_auto_mode_key)
        if not actual_step_to_terminate_key and self.process_info[step_key]['status'] == 'pending_gpu':
            actual_step_to_terminate_key = step_key
        if not actual_step_to_terminate_key:
            return False, None, "Aucune étape active à annuler."
        actual_info_to_terminate = self.process_info[actual_step_to_terminate_key]
        process_to_kill = actual_info_to_terminate.get('process')
        if process_to_kill and process_to_kill.poll() is None:
            try:
                self._logger.info(f"Envoi de SIGTERM à {actual_step_to_terminate_key} (PID: {process_to_kill.pid})")
                process_to_kill.terminate()
                try:
                    process_to_kill.wait(timeout=5)
                    self._logger.info(f"Processus {actual_step_to_terminate_key} terminé après SIGTERM.")
                except Exception:
                    self._logger.warning(f"Processus {actual_step_to_terminate_key} non terminé après SIGTERM, envoi de SIGKILL.")
                    actual_info_to_terminate['log'].append("\n--- Forçage (SIGKILL) après échec SIGTERM ---")
                    process_to_kill.kill()
                    process_to_kill.wait()
                    self._logger.info(f"Processus {actual_step_to_terminate_key} terminé après SIGKILL.")
            except Exception as e:
                actual_info_to_terminate['status'] = 'failed'
                actual_info_to_terminate['log'].append(f"Erreur lors de l'annulation: {str(e)}")
                return False, actual_step_to_terminate_key, "Erreur lors de l'annulation de l'étape."
        actual_info_to_terminate['status'] = 'canceled'
        actual_info_to_terminate['log'].append("Étape annulée par l'utilisateur.")
        return True, actual_step_to_terminate_key, None

    def get_process_info_summary(self):
        return {
            step_key: {
                "status": info["status"],
                "progress_current": info["progress_current"],
                "progress_total": info["progress_total"],
                "progress_text": info["progress_text"],
                "log": list(info["log"])
            } for step_key, info in self.process_info.items()
        }

    def run_process_async(self, step_key, is_auto_mode_step=False, sequence_type=None):
        """Lance un processus de manière asynchrone"""
        if step_key not in self.process_info:
            self._logger.error(f"Étape inconnue: {step_key}")
            return False
            
        info = self.process_info[step_key]
        
        # Check if cmd exists in the process info
        if 'cmd' not in info or not info['cmd']:
            self._logger.error(f"Erreur: Commande non définie pour l'étape {step_key}")
            info['status'] = 'failed'
            info['log'].append(f"ERREUR: Commande non définie pour l'étape {step_key}")
            return False
        
        # Reset process info
        info['status'] = 'initiated'
        info['log'].clear()
        info['return_code'] = None
        info['process'] = None
        info['progress_current'] = 0
        info['progress_total'] = 0
        info['progress_text'] = ''
        info['start_time'] = None
        info['end_time'] = None
        info['duration'] = None
        
        # Start worker thread
        thread = threading.Thread(
            target=self._worker_run_process,
            args=(step_key, is_auto_mode_step, sequence_type),
            daemon=True
        )
        thread.start()
        return True

    def process_step_output_line(self, step_key, line):
        """
        Traite une ligne de sortie d'un processus pour extraire les informations de progression
        
        Args:
            step_key (str): Clé de l'étape
            line (str): Ligne de sortie du processus
        """
        info = self.process_info[step_key]
        patterns = self.config[step_key].get('progress_patterns', {})
        
        # Traitement du pattern 'total'
        if 'total' in patterns:
            m = patterns['total'].search(line)
            if m and m.group(1):
                try:
                    info['progress_total'] = int(m.group(1))
                    self._logger.debug(f"Progression totale pour {step_key}: {info['progress_total']}")
                except (ValueError, IndexError):
                    pass
        
        # Traitement du pattern 'current'
        if 'current' in patterns:
            m = patterns['current'].search(line)
            if m:
                try:
                    groups = m.groups()
                    if len(groups) >= 2:
                        info['progress_current'] = int(groups[0])
                        # Optionnellement mettre à jour progress_total si présent dans le pattern
                        if len(groups) >= 2 and groups[1]:
                            info['progress_total'] = int(groups[1])
                        # Extraire le texte de progression si présent
                        if len(groups) >= 3 and groups[2]:
                            info['progress_text'] = groups[2]
                        self._logger.debug(f"Progression pour {step_key}: {info['progress_current']}/{info['progress_total']} - {info['progress_text']}")
                except (ValueError, IndexError):
                    pass
        
        # Traitement des autres patterns spécifiques
        if 'current_start' in patterns:
            m = patterns['current_start'].search(line)
            if m and patterns.get('current_item_text_from_start', False):
                try:
                    if len(m.groups()) >= 1:
                        info['progress_text'] = m.group(1)
                        self._logger.debug(f"Texte de progression pour {step_key}: {info['progress_text']}")
                except IndexError:
                    pass
        
        if 'current_success_line_pattern' in patterns:
            m = patterns['current_success_line_pattern'].search(line)
            if m and patterns.get('current_item_text_from_success_line', False):
                try:
                    if len(m.groups()) >= 1:
                        info['progress_text'] = m.group(1)
                        info['progress_current'] = info.get('progress_current', 0) + 1
                        self._logger.debug(f"Succès pour {step_key}, progression: {info['progress_current']}/{info['progress_total']} - {info['progress_text']}")
                except IndexError:
                    pass

    def _worker_run_process(self, step_key, is_auto_mode_step=False, sequence_type=None):
        """Exécute un processus dans un thread séparé avec gestion du GPU si nécessaire"""
        info = self.process_info[step_key]
        
        # Check if cmd exists in the process info
        if 'cmd' not in info or not info['cmd']:
            self._logger.error(f"Erreur: Commande non définie pour l'étape {step_key}")
            info['status'] = 'failed'
            info['log'].append(f"ERREUR: Commande non définie pour l'étape {step_key}")
            return
        
        cmd = info['cmd']
        cwd = info.get('cwd', None)
        is_gpu = info.get('gpu_intensive', False)
        
        # Utiliser self.gpu_manager au lieu d'importer depuis app_new
        context = self.gpu_manager.gpu_session(step_key) if is_gpu else contextlib.nullcontext()
        
        try:
            with context:
                self._logger.info(f"Démarrage du processus pour {step_key}: {' '.join(str(c) for c in cmd)}")
                info['status'] = 'running'
                info['start_time'] = time.time()
                
                process = subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Rediriger stderr vers stdout
                    text=True,
                    encoding='utf-8',  # Spécifier l'encodage
                    errors='replace',  # Remplacer les caractères non-UTF8
                    bufsize=1
                )
                
                info['process'] = process
                
                # Lire la sortie ligne par ligne
                for line in process.stdout:
                    if info['status'] == 'canceled':
                        self._logger.info(f"Processus {step_key} annulé, arrêt forcé")
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        break
                    
                    line = line.strip()
                    if line:
                        info['log'].append(line)
                        self.process_step_output_line(step_key, line)
                
                # Attendre la fin du processus
                return_code = process.wait()
                info['return_code'] = return_code
                info['status'] = 'completed' if return_code == 0 else 'failed'
                info['end_time'] = time.time()
                info['duration'] = info['end_time'] - info['start_time']
                
                self._logger.info(f"Processus {step_key} terminé avec code {return_code} en {info['duration']:.2f}s")
                
        except Exception as e:
            self._logger.error(f"Erreur lors de l'exécution de {step_key}: {e}", exc_info=True)
            info['status'] = 'failed'
            info['log'].append(f"ERREUR: {str(e)}")
            if 'start_time' in info and info['start_time'] is not None:
                info['end_time'] = time.time()
                info['duration'] = info['end_time'] - info['start_time']
