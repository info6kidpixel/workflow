import sys
print(f'Python executable: {sys.executable}')
from flask import Flask, render_template, jsonify, request
import contextlib
import csv
import html
import json
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
from pathlib import Path
from datetime import datetime, timezone, timedelta
import uuid
import traceback
import os
import threading
import subprocess
import time
import re
import requests  # Ajout de l'importation manquante
from flask_caching import Cache  # Ajout de l'importation manquante pour Cache
from utils import format_duration_seconds

# Ajoutez cette définition de COMMANDS_CONFIG avant de l'utiliser
# Exemple de configuration des commandes avec des expressions régulières
COMMANDS_CONFIG = {
    "scene_cut": {
        "display_name": "Détection de Scènes",
        "command": [PYTHON_VENV_TRANSNET_EXE, str(BASE_PATH_SCRIPTS / "TransNetV2" / "scene_detect_transnet.py"), "{input_file}"],
        "gpu_intensive": False,
        "progress_regex": re.compile(r"Traitement: (\d+)%"),
        "specific_logs": True
    },
    "tracking": {
        "display_name": "Tracking MediaPipe",
        "command": [PYTHON_VENV_EXE, str(BASE_PATH_SCRIPTS / "tracking_mediapipe_v3.py"), "{input_file}"],
        "gpu_intensive": True,
        "progress_regex": re.compile(r"Frame (\d+)/(\d+)"),
        "specific_logs": True
    },
    "analyze_audio": {
        "display_name": "Analyse Audio",
        "command": [PYTHON_VENV_EXE, str(BASE_PATH_SCRIPTS / "analyze_audio_only8.py"), "{input_file}"],
        "gpu_intensive": True,
        "progress_regex": re.compile(r"Traitement: (\d+)%"),
        "specific_logs": True
    },
    "minify_json": {
        "display_name": "Minification JSON",
        "command": [PYTHON_VENV_EXE, str(BASE_PATH_SCRIPTS / "minify_json.py"), "{input_file}"],
        "gpu_intensive": False,
        "progress_regex": re.compile(r"Traitement: (\d+)%"),
        "specific_logs": False
    },
    "vider_cache": {
        "display_name": "Vider le Cache",
        "command": [PYTHON_VENV_EXE, str(BASE_PATH_SCRIPTS / "vider_cache.py")],
        "gpu_intensive": False,
        "progress_regex": re.compile(r"Nettoyage: (\d+)%"),
        "specific_logs": False
    }
}

# Configuration du système de logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app_debug.log"

# Configuration du logger
logger_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=10*1024*1024, backupCount=5,
    encoding='utf-8'
)
logger_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(threadName)s - %(message)s [in %(pathname)s:%(lineno)d]'
)
logger_handler.setFormatter(logger_formatter)
logger_handler.setLevel(logging.DEBUG)

# Configuration de Flask
app = Flask(__name__)

# Custom JSON encoder to handle non-serializable objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, re.Pattern):
            return str(obj)  # Convert regex pattern to string
        # Add more custom serialization logic if needed
        return super().default(obj)

app.json_encoder = CustomJSONEncoder

@app.route('/')
def index():
    # Vous pouvez toujours passer des variables à votre template si besoin
    localtunnel_active_url = get_localtunnel_url() 
    
    # Le nom du fichier doit correspondre à celui dans le dossier 'templates'
    return render_template('index_new.html', 
                           localtunnel_url=localtunnel_active_url,
                           steps_config=COMMANDS_CONFIG,  # Ajout de la variable steps_config
                           # Vous pouvez passer d'autres variables ici
                           # exemple_variable="Bonjour depuis Flask!"
                          )
    # Vous pouvez rendre un template HTML ici si vous en avez un
    # return render_template('index.html') 
    
    # Ou simplement retourner un message
    localtunnel_active_url = get_localtunnel_url() # Assurez-vous que cette fonction est définie et accessible
    status_message = f"<h1>Application App_New en cours d'exécution</h1>"
    status_message += f"<p>Serveur Flask actif sur le port 5000.</p>"
    if localtunnel_active_url:
        status_message += f"<p>URL Localtunnel active (si démarré): <a href='{localtunnel_active_url}'>{localtunnel_active_url}</a></p>"
    else:
        status_message += f"<p>Localtunnel n'est pas encore actif ou n'a pas pu démarrer.</p>"
    
    status_message += f"<h2>Endpoints API disponibles (exemples):</h2>"
    status_message += f"<ul>"
    status_message += f"<li><a href='/api/get_process_info'>/api/get_process_info</a></li>"
    status_message += f"<li><a href='/api/get_config'>/api/get_config</a></li>"
    # Ajoutez d'autres liens vers vos endpoints si vous le souhaitez
    status_message += f"</ul>"
    return status_message
app.logger.addHandler(logger_handler)
app.logger.setLevel(logging.DEBUG)

# --- Gestion GPU ---
from gpu_manager import GPUManager, GpuUnavailableError
from sequence_manager import SequenceManager
from process_manager import ProcessManager

# Initialisez d'abord gpu_manager
gpu_manager = GPUManager(logger=app.logger, wait_timeout=300)

# Événement pour arrêter proprement l'application
APP_STOP_EVENT = threading.Event()

# URL Localtunnel active
LOCALTUNNEL_URL = None

# Configuration pour l'enregistrement de l'URL Localtunnel
RENDER_REGISTER_URL_ENDPOINT = os.getenv('RENDER_REGISTER_URL_ENDPOINT')
RENDER_REGISTER_TOKEN = os.getenv('RENDER_REGISTER_TOKEN')

# --- Fonctions de Gestion GPU ---

def update_last_sequence_outcome(status, message=None):
    """
    Met à jour le résultat de la dernière séquence exécutée
    
    Args:
        status (str): Le statut de la séquence ('success', 'failed', etc.)
        message (str, optional): Un message descriptif optionnel
    """
    global LAST_SEQUENCE_OUTCOME
    
    LAST_SEQUENCE_OUTCOME = {
        "status": status,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "AutoMode"  # Par défaut, considéré comme AutoMode
    }
    
    # Si nous avons un sequence_manager, mettons également à jour son état
    if 'sequence_manager' in globals():
        sequence_manager.set_last_outcome(LAST_SEQUENCE_OUTCOME)
    
    app.logger.info(f"Résultat de séquence mis à jour: {status} - {message}")

def check_and_launch_pending_gpu_task() -> None:
    """Vérifie et lance une tâche GPU en attente si possible"""
    try:
        # Vérifier si une tâche GPU est en attente
        with gpu_manager._gpu_lock:
            if not gpu_manager._gpu_waiting_queue:
                return
            
            # Si le GPU est déjà utilisé, ne rien faire
            if gpu_manager.current_user:
                return
            
            # Récupérer la première tâche en attente
            step_key = gpu_manager._gpu_waiting_queue[0]
        
        # Vérifier si cette tâche fait partie d'une séquence auto
        is_auto_mode_step = step_key == sequence_manager.get_current_auto_mode_key()
        
        # Lancer la tâche
        app.logger.info(f"Lancement de la tâche GPU en attente: {step_key}")
        process_manager.run_process_async(step_key, is_auto_mode_step=is_auto_mode_step, sequence_type="AutoMode" if is_auto_mode_step else "Manual")
        
    except Exception as e:
        app.logger.error(f"Erreur lors du lancement de la tâche GPU en attente: {e}", exc_info=True)
        
        # Mettre à jour l'état de la séquence si c'est une étape auto mode
        if is_auto_mode_step:
            update_last_sequence_outcome("failed", f"Échec au lancement de l'étape GPU {step_key}: {str(e)}")

# --- Configuration Globale de l'Application ---
BASE_PATH_SCRIPTS_ENV = os.environ.get('BASE_PATH_SCRIPTS_ENV', "F:/test_mediapipe")
BASE_PATH_SCRIPTS = Path(BASE_PATH_SCRIPTS_ENV)
PYTHON_VENV_EXE_ENV = os.environ.get('PYTHON_VENV_EXE_ENV', str(BASE_PATH_SCRIPTS / ".venv_audio" / "Scripts" / "python.exe"))
PYTHON_VENV_EXE = PYTHON_VENV_EXE_ENV
PYTHON_VENV_TRANSNET_EXE_ENV = os.environ.get('PYTHON_VENV_TRANSNET_EXE_ENV', str(BASE_PATH_SCRIPTS / "TransNetV2" / "venv_transnet" / "Scripts" / "python.exe"))
PYTHON_VENV_TRANSNET_EXE = PYTHON_VENV_TRANSNET_EXE_ENV
AUDIO_ANALYSIS_LOG_DIR_ENV = os.environ.get('AUDIO_ANALYSIS_LOG_DIR_ENV', str(BASE_PATH_SCRIPTS / "logs_audio_tv"))
AUDIO_ANALYSIS_LOG_DIR = Path(AUDIO_ANALYSIS_LOG_DIR_ENV)
AERENDER_LOGS_DIR_ENV = os.environ.get('AERENDER_LOGS_DIR_ENV', str(BASE_PATH_SCRIPTS / "logs_watchfolder"))
AERENDER_LOGS_DIR = Path(AERENDER_LOGS_DIR_ENV)
AERENDER_JOBS_LOGS_DIR = AERENDER_LOGS_DIR / "aerender_jobs_logs"
STEP0_PREP_LOG_DIR_ENV = os.environ.get('STEP0_PREP_LOG_DIR_ENV', str(BASE_PATH_SCRIPTS / "_MediaSolution_Step1_Logs"))
STEP0_PREP_LOG_DIR = Path(STEP0_PREP_LOG_DIR_ENV)
BASE_TRACKING_LOG_SEARCH_PATH_ENV = os.environ.get('BASE_TRACKING_LOG_SEARCH_PATH_ENV', "F:/")
BASE_TRACKING_LOG_SEARCH_PATH = Path(BASE_TRACKING_LOG_SEARCH_PATH_ENV)
BASE_TRACKING_PROGRESS_SEARCH_PATH_ENV = os.environ.get('BASE_TRACKING_PROGRESS_SEARCH_PATH_ENV', "F:/")
BASE_TRACKING_PROGRESS_SEARCH_PATH = Path(BASE_TRACKING_PROGRESS_SEARCH_PATH_ENV)
HF_AUTH_TOKEN_ENV = os.environ.get("HF_AUTH_TOKEN") # Garder os.environ.get, pas de fallback pour celui-ci
DEFAULT_HF_TOKEN = "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" # Default si HF_AUTH_TOKEN_ENV n'est pas défini
LOCAL_DROPBOX_DOWNLOAD_DIR_ENV = os.environ.get('LOCAL_DROPBOX_DOWNLOAD_DIR_ENV', str(BASE_PATH_SCRIPTS / "Dropbox_Downloads_From_Render"))
LOCAL_DROPBOX_DOWNLOAD_DIR = Path(LOCAL_DROPBOX_DOWNLOAD_DIR_ENV)
LOCAL_DROPBOX_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Default/Reference tokens if not set by environment variables
# These are primarily for internal logic to check if a fallback was used
# and if that fallback itself was empty.
REF_LOCAL_DOWNLOAD_API_TOKEN_NEW = ""
REF_RENDER_REGISTER_TOKEN_NEW = ""
REF_INTERNAL_WORKER_COMMS_TOKEN_NEW = "" # This remains ""

# Utilisation des tokens avec fallback
LOCAL_DOWNLOAD_API_TOKEN_ENV = os.environ.get("LOCAL_DOWNLOAD_API_TOKEN", REF_LOCAL_DOWNLOAD_API_TOKEN_NEW)
RENDER_APP_CALLBACK_URL_ENV = os.environ.get("RENDER_APP_CALLBACK_URL") # Pour notifier app_render après DL
RENDER_APP_CALLBACK_TOKEN_ENV = os.environ.get("RENDER_APP_CALLBACK_TOKEN") # Token pour cette notification (pourrait être PROCESS_API_TOKEN)

RENDER_REGISTER_URL_ENDPOINT_ENV = os.environ.get("RENDER_REGISTER_URL_ENDPOINT") # URL où app_new enregistre son LT URL
RENDER_REGISTER_TOKEN_ENV = os.environ.get("RENDER_REGISTER_TOKEN", REF_RENDER_REGISTER_TOKEN_NEW) # Token pour cet enregistrement

LT_PROCESS = None
LT_URL = None
LT_URL_LOCK = threading.Lock()

LOG_BASE_DIRECTORY_VIDER_CACHE = r'F:\test_mediapipe\log_vide_cache'
LOG_FILENAME_PREFIX_VIDER_CACHE = 'cache_cleanup_log'
LOG_FILE_EXTENSION_VIDER_CACHE = '.txt'

ACTIVE_LOCAL_DOWNLOADS = {}
KEPT_DOWNLOAD_STATUSES_DEQUE = deque(maxlen=20)
LOCAL_DOWNLOADS_LOCK = threading.Lock()

AUTO_MODE_ENABLED = True
AUTO_MODE_LOCK = threading.Lock()
AUTO_MODE_TRIGGER_QUEUE = deque()
AUTO_MODE_QUEUE_LOCK = threading.Lock()
CURRENT_AUTO_MODE_ACTIVE_STEP_KEY = None
AUTO_MODE_ACTIVE_STEP_LOCK = threading.Lock()
LAST_SEQUENCE_OUTCOME = {"status": "never_run", "timestamp": None}

INTERNAL_WORKER_COMMS_TOKEN_ENV = os.environ.get("INTERNAL_WORKER_COMMS_TOKEN", REF_INTERNAL_WORKER_COMMS_TOKEN_NEW) # This will pick up the env var if set

# Configuration du cache
CACHE_CONFIG = { "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300 }
app.config.from_mapping(CACHE_CONFIG)
cache = Cache(app)

# Journalisation des exceptions non gérées
def log_uncaught_exceptions(ex_cls, ex, tb):
    app.logger.critical(''.join(traceback.format_tb(tb)))
    app.logger.critical('{0}: {1}'.format(ex_cls, ex))

sys.excepthook = log_uncaught_exceptions

# --- Configuration Tokens & Logging ---
app.logger.info("--- Initialisation Configuration Tokens ---")

def get_token_with_fallback(env_var, ref_value, default=None, token_name="TOKEN"):
    """Centralise la logique de fallback pour les tokens et log la source."""
    value = os.environ.get(env_var)
    if value:
        app.logger.info(f"{token_name}: Défini via variable d'environnement.")
        return value
    if ref_value:
        app.logger.warning(f"{token_name}: Non défini en env, fallback sur valeur de référence.")
        return ref_value
    if default:
        app.logger.warning(f"{token_name}: Non défini en env ni ref, fallback sur valeur par défaut codée.")
        return default
    app.logger.error(f"{token_name}: Non défini, fallback vide !")
    return ""

# Utilisation centralisée pour chaque token
HF_AUTH_TOKEN_ENV = get_token_with_fallback("HF_AUTH_TOKEN", None, DEFAULT_HF_TOKEN, "HF_AUTH_TOKEN")
LOCAL_DOWNLOAD_API_TOKEN_ENV = get_token_with_fallback("LOCAL_DOWNLOAD_API_TOKEN", REF_LOCAL_DOWNLOAD_API_TOKEN_NEW, None, "LOCAL_DOWNLOAD_API_TOKEN")
RENDER_REGISTER_TOKEN_ENV = get_token_with_fallback("RENDER_REGISTER_TOKEN", REF_RENDER_REGISTER_TOKEN_NEW, None, "RENDER_REGISTER_TOKEN")
INTERNAL_WORKER_COMMS_TOKEN_ENV = get_token_with_fallback("INTERNAL_WORKER_COMMS_TOKEN", REF_INTERNAL_WORKER_COMMS_TOKEN_NEW, None, "INTERNAL_WORKER_COMMS_TOKEN")

# Default/Reference tokens if not set by environment variables
# These are primarily for internal logic to check if a fallback was used
# and if that fallback itself was empty.
REF_LOCAL_DOWNLOAD_API_TOKEN_NEW = ""
REF_RENDER_REGISTER_TOKEN_NEW = ""
REF_INTERNAL_WORKER_COMMS_TOKEN_NEW = "" # This remains ""

# Utilisation des tokens avec fallback
LOCAL_DOWNLOAD_API_TOKEN_ENV = os.environ.get("LOCAL_DOWNLOAD_API_TOKEN", REF_LOCAL_DOWNLOAD_API_TOKEN_NEW)
RENDER_APP_CALLBACK_URL_ENV = os.environ.get("RENDER_APP_CALLBACK_URL") # Pour notifier app_render après DL
RENDER_APP_CALLBACK_TOKEN_ENV = os.environ.get("RENDER_APP_CALLBACK_TOKEN") # Token pour cette notification (pourrait être PROCESS_API_TOKEN)

RENDER_REGISTER_URL_ENDPOINT_ENV = os.environ.get("RENDER_REGISTER_URL_ENDPOINT") # URL où app_new enregistre son LT URL
RENDER_REGISTER_TOKEN_ENV = os.environ.get("RENDER_REGISTER_TOKEN", REF_RENDER_REGISTER_TOKEN_NEW) # Token pour cet enregistrement

LT_PROCESS = None
LT_URL = None
LT_URL_LOCK = threading.Lock()

LOG_BASE_DIRECTORY_VIDER_CACHE = r'F:\test_mediapipe\log_vide_cache'
LOG_FILENAME_PREFIX_VIDER_CACHE = 'cache_cleanup_log'
LOG_FILE_EXTENSION_VIDER_CACHE = '.txt'

ACTIVE_LOCAL_DOWNLOADS = {}
KEPT_DOWNLOAD_STATUSES_DEQUE = deque(maxlen=20)
LOCAL_DOWNLOADS_LOCK = threading.Lock()

AUTO_MODE_ENABLED = True
AUTO_MODE_LOCK = threading.Lock()
AUTO_MODE_TRIGGER_QUEUE = deque()
AUTO_MODE_QUEUE_LOCK = threading.Lock()
CURRENT_AUTO_MODE_ACTIVE_STEP_KEY = None
AUTO_MODE_ACTIVE_STEP_LOCK = threading.Lock()
LAST_SEQUENCE_OUTCOME = {"status": "never_run", "timestamp": None}

INTERNAL_WORKER_COMMS_TOKEN_ENV = os.environ.get("INTERNAL_WORKER_COMMS_TOKEN", REF_INTERNAL_WORKER_COMMS_TOKEN_NEW) # This will pick up the env var if set

# Configuration du cache
CACHE_CONFIG = { "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300 }
app.config.from_mapping(CACHE_CONFIG)
cache = Cache(app)

# Journalisation des exceptions non gérées
def log_uncaught_exceptions(ex_cls, ex, tb):
    app.logger.critical(''.join(traceback.format_tb(tb)))
    app.logger.critical('{0}: {1}'.format(ex_cls, ex))

# --- Configuration Tokens & Logging ---
app.logger.info("--- Initialisation Configuration Tokens ---")

# HF_AUTH_TOKEN
if not HF_AUTH_TOKEN_ENV:
    app.logger.info("HF_AUTH_TOKEN: Non défini via variable d'environnement. Utilisation du token par défaut codé en dur pour Analyze Audio.")
    HF_AUTH_TOKEN_ENV = DEFAULT_HF_TOKEN
elif HF_AUTH_TOKEN_ENV == DEFAULT_HF_TOKEN:
     app.logger.info("HF_AUTH_TOKEN: Variable d'environnement définie sur le token par défaut codé en dur.")
else:
    app.logger.info("HF_AUTH_TOKEN: Variable d'environnement trouvée et sera utilisée pour Analyze Audio.")

# LOCAL_DOWNLOAD_API_TOKEN
token_value_to_check = LOCAL_DOWNLOAD_API_TOKEN_ENV
ref_value_for_local_dl = REF_LOCAL_DOWNLOAD_API_TOKEN_NEW if REF_LOCAL_DOWNLOAD_API_TOKEN_NEW else "fallback_was_empty"

if not token_value_to_check or \
   (token_value_to_check == ref_value_for_local_dl and not REF_LOCAL_DOWNLOAD_API_TOKEN_NEW):
    app.logger.warning("LOCAL_DOWNLOAD_API_TOKEN: Non défini ou utilise un fallback vide! Endpoint de téléchargement local NON SÉCURISÉ. Définir via variable d'environnement LOCAL_DOWNLOAD_API_TOKEN.")
elif token_value_to_check == "YOUR_SECRET_TOKEN_FOR_LOCAL_PC": # Ancien placeholder
    app.logger.warning("LOCAL_DOWNLOAD_API_TOKEN: Utilise un placeholder par défaut! Endpoint de téléchargement local NON SÉCURISÉ. Définir un token unique via LOCAL_DOWNLOAD_API_TOKEN.")
else:
    app.logger.info(f"LOCAL_DOWNLOAD_API_TOKEN: Configuré ('...{token_value_to_check[-5:]}'). Endpoint de téléchargement local sécurisé.")

# RENDER_REGISTER_URL_ENDPOINT & RENDER_REGISTER_TOKEN
if not RENDER_REGISTER_URL_ENDPOINT_ENV or not RENDER_REGISTER_TOKEN_ENV or \
   (RENDER_REGISTER_TOKEN_ENV == REF_RENDER_REGISTER_TOKEN_NEW and not REF_RENDER_REGISTER_TOKEN_NEW):
    app.logger.warning("RENDER_REGISTER_URL_ENDPOINT ou RENDER_REGISTER_TOKEN: Non configuré ou token de fallback vide. L'URL Localtunnel ne sera pas enregistrée sur le serveur Render.")
else:
    app.logger.info(f"RENDER_REGISTER: URL ('{RENDER_REGISTER_URL_ENDPOINT_ENV}') et Token ('...{RENDER_REGISTER_TOKEN_ENV[-5:]}') configurés pour l'enregistrement Localtunnel.")

# INTERNAL_WORKER_COMMS_TOKEN
token_value_to_check_internal = INTERNAL_WORKER_COMMS_TOKEN_ENV
# ref_value_for_internal logic remains the same.
# If INTERNAL_WORKER_COMMS_TOKEN is set in .bat, token_value_to_check_internal will not be empty.
# The "not token_value_to_check_internal" part of the 'if' will be false.
# The second part of the 'if' "(token_value_to_check_internal == ref_value_for_internal and not REF_INTERNAL_WORKER_COMMS_TOKEN_NEW)"
# will also be false because token_value_to_check_internal (from env) will not be equal to ref_value_for_internal ("fallback_was_empty" if REF is empty, or REF itself if not empty).
# So, the 'else' branch should be taken if the env var is set to a non-empty string.

if not token_value_to_check_internal or \
   (token_value_to_check_internal == (REF_INTERNAL_WORKER_COMMS_TOKEN_NEW if REF_INTERNAL_WORKER_COMMS_TOKEN_NEW else "fallback_was_empty") and not REF_INTERNAL_WORKER_COMMS_TOKEN_NEW):
    app.logger.warning("INTERNAL_WORKER_COMMS_TOKEN: Non défini ou utilise un fallback vide. Endpoint /api/get_remote_status_summary NON SÉCURISÉ et acceptera les appels sans token.")
else:
    app.logger.info(f"INTERNAL_WORKER_COMMS_TOKEN: Configuré ('...{token_value_to_check_internal[-5:]}') pour /api/get_remote_status_summary.")

app.logger.info("--- Fin Initialisation Configuration Tokens ---")

REMOTE_TRIGGER_URL_ENV = os.environ.get('REMOTE_TRIGGER_URL', "https://render-signal-server.onrender.com/api/check_trigger")
REMOTE_TRIGGER_URL = REMOTE_TRIGGER_URL_ENV
REMOTE_POLLING_INTERVAL = int(os.environ.get('REMOTE_POLLING_INTERVAL', "15"))
REMOTE_SEQUENCE_STEP_KEYS = ["preparation_dezip", "scene_cut", "analyze_audio", "tracking", "minify_json"]
is_currently_running_any_sequence = False
sequence_lock = threading.Lock()

# --- Fonctions Utilitaires (format_duration, create_frontend_safe_config, sanitize_filename_local) ---
# (Ces fonctions sont identiques à la version précédente)
def create_frontend_safe_config(config_dict: dict) -> dict:
    frontend_config = {}
    for step_key, step_data_orig in config_dict.items():
        frontend_step_data = {}
        for key, value in step_data_orig.items():
            if key == "progress_regex":
                pass
            elif isinstance(value, Path):
                frontend_step_data[key] = str(value)
            elif key == "command" and isinstance(value, list):
                frontend_step_data[key] = [str(item) for item in value]
            elif key == "specific_logs" and isinstance(value, bool):
                frontend_step_data[key] = value
            else:
                frontend_step_data[key] = value
        frontend_config[step_key] = frontend_step_data
    return frontend_config

def sanitize_filename_local(filename_str, max_length=230):
    if filename_str is None:
        app.logger.warning("sanitize_filename_local: filename_str was None, using default 'fichier_nom_absent'.")
        filename_str = "fichier_nom_absent"
    s = str(filename_str).strip().replace(' ', '_')
    s = re.sub(r'(?u)[^-\w.]', '', s)
    if not s:
        s = "fichier_sans_nom_valide"
        app.logger.warning(f"sanitize_filename_local: Sanitized filename was empty for input '{filename_str}', using '{s}'.")
    if len(s) > max_length:
        original_full_name_for_log = s
        name_part, ext_part = os.path.splitext(s)
        max_name_len = max_length - len(ext_part) - (1 if ext_part else 0)
        if max_name_len < 1:
            s = s[:max_length]
        else:
            s = name_part[:max_name_len] + ext_part
        app.logger.info(f"sanitize_filename_local: Filename '{original_full_name_for_log}' truncated to '{s}' (max_length: {max_length}).")
    return s

# --- Gestion Localtunnel (get_localtunnel_url, set_localtunnel_url, manage_localtunnel_and_register) ---
# (Ces fonctions sont identiques, manage_localtunnel_and_register utilisera RENDER_REGISTER_URL_ENDPOINT_ENV et RENDER_REGISTER_TOKEN_ENV chargés plus haut)
def get_localtunnel_url():
    global LT_URL
    with LT_URL_LOCK:
        return LT_URL

def set_localtunnel_url(url):
    global LT_URL
    with LT_URL_LOCK:
        LT_URL = url
    if url: app.logger.info(f"LOCALTUNNEL_MGR: URL Localtunnel active mise à jour à: {url}")
    else: app.logger.info("LOCALTUNNEL_MGR: URL Localtunnel désactivée (None).")

def try_unregister_url(url):
    """Tentative de désenregistrement de l'URL sur le serveur Render avec gestion améliorée des erreurs."""
    if not url:
        app.logger.warning("try_unregister_url: URL vide fournie, désenregistrement ignoré")
        return False

    if not RENDER_REGISTER_URL_ENDPOINT_ENV or not RENDER_REGISTER_TOKEN_ENV:
        app.logger.warning("try_unregister_url: Configuration d'enregistrement Render manquante")
        return False

    try:
        unregister_payload = {
            "localtunnel_url": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_url": url
        }
        
        unregister_headers = {
            "X-Register-Token": RENDER_REGISTER_TOKEN_ENV,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            RENDER_REGISTER_URL_ENDPOINT_ENV,
            json=unregister_payload,
            headers=unregister_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            app.logger.info(f"URL désenregistrée avec succès: {url}")
            return True
        else:
            app.logger.warning(
                f"Échec désenregistrement URL {url} - "
                f"Status: {response.status_code}, "
                f"Réponse: {response.text[:200]}"
            )
            return False
            
    except requests.exceptions.Timeout:
        app.logger.error(f"Timeout lors du désenregistrement de l'URL {url}")
        return False
        
    except requests.exceptions.RequestException as e_unreg:
        app.logger.error(f"Erreur lors du désenregistrement de l'URL {url}: {e_unreg}")
        return False
        
    except Exception as e:
        app.logger.error(f"Erreur inattendue lors du désenregistrement de l'URL {url}: {e}", exc_info=True)
        return False

def find_localtunnel_executable():
    """Recherche l'exécutable localtunnel dans les emplacements possibles."""
    npm_global_path_str = os.path.join(os.environ.get('APPDATA', ''), 'npm')
    
    # Chemins à vérifier, avec une priorité pour lt.cmd dans le dossier npm global
    # puis lt.cmd dans le PATH, puis lt dans le PATH.
    paths_to_check = [
        os.path.join(npm_global_path_str, "lt.cmd"), # Chemin complet vers lt.cmd
        "lt.cmd",                                   # lt.cmd via PATH
        "lt",                                       # lt via PATH (pourrait être lt.exe ou autre)
    ]

    app.logger.debug(f"LOCALTUNNEL_MGR: Chemins de recherche pour lt: {paths_to_check}")

    for p_candidate_str in paths_to_check:
        try:
            # Pour les chemins absolus, vérifier simplement l'existence du fichier
            if os.path.isabs(p_candidate_str):
                if os.path.isfile(p_candidate_str):
                    app.logger.info(f"LOCALTUNNEL_MGR: Exécutable trouvé (chemin absolu): {p_candidate_str}")
                    return p_candidate_str
                else:
                    app.logger.debug(f"LOCALTUNNEL_MGR: Chemin absolu non trouvé ou n'est pas un fichier: {p_candidate_str}")
                    continue # Passer au candidat suivant

            # Pour les noms de commandes (non absolus), essayer de les exécuter pour voir si le système les trouve via le PATH
            # Utiliser shell=True est généralement déconseillé pour des raisons de sécurité si l'entrée est variable,
            # mais ici la commande est fixe ("lt.cmd --version" ou "lt --version").
            # On capture la sortie pour éviter qu'elle n'apparaisse dans la console principale.
            # Le timeout évite de bloquer indéfiniment.
            cmd_to_try = [p_candidate_str, "--version"]
            app.logger.debug(f"LOCALTUNNEL_MGR: Tentative de vérification via PATH: {' '.join(cmd_to_try)}")
            
            # Windows a besoin de shell=True pour trouver .cmd dans le PATH sans spécifier l'extension
            # ou si on utilise directement le nom de la commande.
            process = subprocess.Popen(cmd_to_try, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate(timeout=5) # Attendre la fin avec timeout

            if process.returncode == 0:
                app.logger.info(f"LOCALTUNNEL_MGR: Exécutable '{p_candidate_str}' trouvé via PATH et répond à --version.")
                return p_candidate_str # Retourner le nom de la commande (ex: "lt.cmd")
            else:
                app.logger.debug(f"LOCALTUNNEL_MGR: '{p_candidate_str} --version' a échoué avec code {process.returncode}. Stdout: {stdout.strip()}, Stderr: {stderr.strip()}")

        except FileNotFoundError:
            app.logger.debug(f"LOCALTUNNEL_MGR: '{p_candidate_str}' non trouvé (FileNotFoundError lors de Popen).")
        except subprocess.TimeoutExpired:
            app.logger.warning(f"LOCALTUNNEL_MGR: Timeout en vérifiant '{p_candidate_str}'.")
            if process: # s'assurer que process est défini
                process.kill() # Tuer le processus en cas de timeout
                process.communicate() # Nettoyer
        except Exception as e:
            app.logger.error(f"LOCALTUNNEL_MGR: Erreur inattendue en cherchant '{p_candidate_str}': {e}", exc_info=False) # Mettre exc_info=True pour plus de détails si besoin
            # Logguer l'exception complète si en mode debug avancé
            if app.logger.getEffectiveLevel() <= logging.DEBUG:
                 app.logger.exception(f"Exception détaillée pour {p_candidate_str}:")


    app.logger.error("LOCALTUNNEL_MGR: Exécutable 'lt' ou 'lt.cmd' NON TROUVÉ.")
    return None

def register_localtunnel_url(new_url):
    """Enregistre l'URL localtunnel auprès du service externe."""
    if not (RENDER_REGISTER_URL_ENDPOINT_ENV and RENDER_REGISTER_TOKEN_ENV):
        app.logger.info(f"LOCALTUNNEL_MGR: URL obtenue mais pas d'enregistrement configuré: {new_url}")
        return True

    try:
        register_payload = {
            "localtunnel_url": new_url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        register_headers = {
            "X-Register-Token": RENDER_REGISTER_TOKEN_ENV,
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            RENDER_REGISTER_URL_ENDPOINT_ENV,
            json=register_payload,
            headers=register_headers,
            timeout=10
        )
        
        if response.status_code == 200:
            app.logger.info(f"LOCALTUNNEL_MGR: URL {new_url} enregistrée avec succès")
            return True
        else:
            app.logger.error(
                f"LOCALTUNNEL_MGR: Échec enregistrement URL {new_url} - "
                f"Status: {response.status_code}, "
                f"Réponse: {response.text[:200]}"
            )
            return False
            
    except Exception as e:
        app.logger.error(f"LOCALTUNNEL_MGR: Erreur lors de l'enregistrement de l'URL: {e}")
        return False

def cleanup_localtunnel_process(process):
    """Nettoie proprement un processus localtunnel."""
    if process and process.poll() is None:
        app.logger.info("LOCALTUNNEL_MGR: Tentative d'arrêt gracieux du processus...")
        try:
            process.terminate()
            try:
                process.wait(timeout=5)
                return True
            except subprocess.TimeoutExpired:
                app.logger.warning("LOCALTUNNEL_MGR: Timeout lors de la terminaison, tentative de kill")
                process.kill()
                process.wait(timeout=5)
                return True
        except Exception as e:
            app.logger.error(f"LOCALTUNNEL_MGR: Erreur lors du nettoyage du processus: {e}")
            return False
    return True

def manage_localtunnel_and_register():
    """Gère le processus localtunnel avec une meilleure gestion des erreurs et des redémarrages."""
    consecutive_failures = 0
    current_url = None
    current_process = None

    while not APP_STOP_EVENT.is_set():
        try:
            # Vérification de l'exécutable lt
            lt_cmd = find_localtunnel_executable()
            if not lt_cmd:
                raise FileNotFoundError("Commande 'lt' (localtunnel) non trouvée. NPM est-il installé et lt installé globalement?")

            app.logger.info(f"LOCALTUNNEL_MGR: Démarrage avec la commande: {lt_cmd}")
            cmd = [lt_cmd, "--port", "5000"]
            current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            app.logger.info(f"LOCALTUNNEL_MGR: Processus démarré (PID: {current_process.pid})")

            while not APP_STOP_EVENT.is_set() and current_process.poll() is None:
                line = current_process.stdout.readline().strip()
                if not line:
                    continue

                app.logger.debug(f"LOCALTUNNEL_OUT: {line}")
                
                if "your url is:" in line.lower():
                    new_url = line.split("is:")[-1].strip()
                    if new_url != current_url:
                        # Désenregistrer l'ancienne URL si elle existe
                        if current_url:
                            try_unregister_url(current_url)
                        
                        # Enregistrer et activer la nouvelle URL
                        if register_localtunnel_url(new_url):
                            current_url = new_url
                            set_localtunnel_url(new_url)
                            consecutive_failures = 0

            # Vérification de l'état de sortie
            return_code = current_process.poll()
            if return_code is not None:
                app.logger.warning(f"LOCALTUNNEL_MGR: Processus terminé avec code {return_code}")
                consecutive_failures += 1

        except FileNotFoundError as e:
            app.logger.error(f"LOCALTUNNEL_MGR: {str(e)}")
            consecutive_failures += 1
            
        except Exception as e:
            app.logger.error(f"LOCALTUNNEL_MGR: Erreur inattendue: {str(e)}", exc_info=True)
            consecutive_failures += 1
            
            cleanup_localtunnel_process(current_process)

        finally:
            # Nettoyage et délai adaptatif avant nouvelle tentative
            if current_url:
                try_unregister_url(current_url)
                current_url = None
                set_localtunnel_url(None)

            if not APP_STOP_EVENT.is_set():
                delay = min(15 * (2 ** consecutive_failures), 300)  # Max 5 minutes
                app.logger.info(f"LOCALTUNNEL_MGR: Attente de {delay}s avant relance (échecs consécutifs: {consecutive_failures})")
                APP_STOP_EVENT.wait(delay)

# Après avoir défini COMMANDS_CONFIG, initialisez process_manager
process_manager = ProcessManager(config=COMMANDS_CONFIG, logger=app.logger, gpu_manager=gpu_manager)

# Puis initialisez sequence_manager si nécessaire
sequence_manager = SequenceManager(process_manager=process_manager, logger=app.logger)

# Configuration du GPU Manager (après que les dépendances soient définies)
if 'gpu_manager' in globals() and hasattr(gpu_manager, 'set_commands_config'):
    gpu_manager.set_commands_config(COMMANDS_CONFIG)
if 'gpu_manager' in globals() and hasattr(gpu_manager, 'set_app_stop_event'):
    gpu_manager.set_app_stop_event(APP_STOP_EVENT)

@app.route('/cancel/<step_key>', methods=['POST'])
def cancel_step(step_key):
    """
    Annule proprement l'étape en cours (ou l'étape active de la séquence) :
    - Termine le processus système (subprocess.Popen) associé à l'étape
    - Libère le GPU si besoin
    - Met à jour l'état global
    """
    with sequence_manager.lock():
        if not sequence_manager.is_running():
            return jsonify({"success": False, "message": "Aucune séquence en cours."}), 400
        current_auto_mode_key = sequence_manager.get_current_auto_mode_key()
        success, actual_step_key, error_msg = process_manager.cancel_step(step_key, current_auto_mode_key)
        if not success:
            return jsonify({"success": False, "message": error_msg or "Erreur lors de l'annulation."}), 400
        info = process_manager.process_info[actual_step_key]
        return jsonify({
            "success": True,
            "step_key": actual_step_key,
            "status": info['status'],
            "log": list(info['log'])
        }), 200

@app.route('/api/get_remote_status_summary', methods=['GET'])
def get_remote_status_summary():
    """
    Résumé de l'état distant pour le tableau de bord.
    - Indique si le rendu est en cours sur une machine distante
    - Fournit l'état des étapes clés
    """
    global REMOTE_TRIGGER_URL_ENV, REMOTE_POLLING_INTERVAL
    try:
        # Vérifier si l'URL de déclenchement est définie
        if not REMOTE_TRIGGER_URL_ENV:
            return jsonify({"error": "URL de déclenchement distante non configurée."}), 500

        # Appel à l'API distante pour obtenir l'état
        response = requests.get(REMOTE_TRIGGER_URL_ENV, timeout=10)
        response.raise_for_status()  # Provoque une erreur pour les codes 4xx/5xx

        # Traiter la réponse JSON
        remote_status = response.json()
        app.logger.info(f"Statut distant obtenu: {remote_status}")

        return jsonify(remote_status), 200

    except requests.exceptions.Timeout:
        app.logger.error("Délai d'attente dépassé lors de la communication avec le serveur distant.")
        return jsonify({"error": "Délai d'attente dépassé."}), 504

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erreur lors de la communication avec le serveur distant: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        app.logger.error(f"Erreur inattendue: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/trigger_render_sequence', methods=['POST'])
def trigger_render_sequence():
    """
    Déclenche manuellement une séquence de rendu sur la machine distante.
    - Attendu que le client envoie une liste d'étapes à exécuter
    - Retourne l'état de la soumission
    """
    global REMOTE_TRIGGER_URL_ENV, REMOTE_POLLING_INTERVAL
    try:
        # Vérifier si l'URL de déclenchement est définie
        if not REMOTE_TRIGGER_URL_ENV:
            return jsonify({"error": "URL de déclenchement distante non configurée."}), 500

        # Obtenir les données JSON de la requête
        data = request.get_json()
        steps_to_run = data.get("steps", [])
        app.logger.info(f"Reçu demande de déclenchement pour les étapes: {steps_to_run}")

        # Validation simple
        if not isinstance(steps_to_run, list) or not all(isinstance(step, str) for step in steps_to_run):
            return jsonify({"error": "Données de demande invalides. Attendu une liste d'étapes."}), 400

        # Appel à l'API distante pour déclencher la séquence
        response = requests.post(
            REMOTE_TRIGGER_URL_ENV,
            json={"steps": steps_to_run},
            timeout=10
        )
        response.raise_for_status()  # Provoque une erreur pour les codes 4xx/5xx

        # Traiter la réponse JSON
        result = response.json()
        app.logger.info(f"Résultat de la soumission: {result}")

        return jsonify(result), 200

    except requests.exceptions.Timeout:
        app.logger.error("Délai d'attente dépassé lors de la communication avec le serveur distant.")
        return jsonify({"error": "Délai d'attente dépassé."}), 504

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erreur lors de la communication avec le serveur distant: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        app.logger.error(f"Erreur inattendue: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/cancel_render_sequence', methods=['POST'])
def cancel_render_sequence():
    """
    Annule une séquence de rendu en cours sur la machine distante.
    - Appelle l'API distante pour annuler le rendu
    - Retourne l'état de l'annulation
    """
    global REMOTE_TRIGGER_URL_ENV
    try:
        # Vérifier si l'URL de déclenchement est définie
        if not REMOTE_TRIGGER_URL_ENV:
            return jsonify({"error": "URL de déclenchement distante non configurée."}), 500

        # Appel à l'API distante pour annuler la séquence
        response = requests.post(
            f"{REMOTE_TRIGGER_URL_ENV}/cancel",
            timeout=10
        )
        response.raise_for_status()  # Provoque une erreur pour les codes 4xx/5xx

        # Traiter la réponse JSON
        result = response.json()
        app.logger.info(f"Résultat de l'annulation: {result}")

        return jsonify(result), 200

    except requests.exceptions.Timeout:
        app.logger.error("Délai d'attente dépassé lors de la communication avec le serveur distant.")
        return jsonify({"error": "Délai d'attente dépassé."}), 504

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erreur lors de la communication avec le serveur distant: {e}")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        app.logger.error(f"Erreur inattendue: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/get_process_info', methods=['GET'])
def get_process_info():
    """
    Retourne les informations sur les processus en cours pour chaque étape.
    - Utilisé pour le tableau de bord et le suivi
    """
    try:
        process_summary = process_manager.get_process_info_summary()
        return jsonify(process_summary), 200
    except Exception as e:
        app.logger.error(f"Erreur inattendue lors de la récupération des infos de processus: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/get_config', methods=['GET'])
def get_config():
    """
    Retourne la configuration actuelle du serveur.
    - Inclut les chemins, tokens, et autres paramètres importants
    """
    try:
        config_safe = {
            "base_paths": {
                "scripts": str(BASE_PATH_SCRIPTS),
                "audio_analysis_logs": str(AUDIO_ANALYSIS_LOG_DIR),
                "aerender_logs": str(AERENDER_LOGS_DIR),
                "step0_prep_logs": str(STEP0_PREP_LOG_DIR),
                "local_dropbox_download": str(LOCAL_DROPBOX_DOWNLOAD_DIR)
            },
            "remote": {
                "trigger_url": REMOTE_TRIGGER_URL_ENV,
                "polling_interval": REMOTE_POLLING_INTERVAL
            },
            "auto_mode": {
                "enabled": AUTO_MODE_ENABLED,
                "current_active_step": sequence_manager.get_current_auto_mode_key()
            },
            "last_sequence_outcome": sequence_manager.get_last_outcome()
        }
        return jsonify(config_safe), 200
    except Exception as e:
        app.logger.error(f"Erreur inattendue lors de la récupération de la config: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/set_auto_mode', methods=['POST'])
def set_auto_mode():
    """
    Active ou désactive le mode automatique.
    - Attend une requête JSON avec le champ "enabled" (booléen)
    """
    global AUTO_MODE_ENABLED
    try:
        data = request.get_json()
        enabled = data.get("enabled", None)

        if enabled is None:
            return jsonify({"error": "Champ 'enabled' manquant dans la requête."}), 400

        AUTO_MODE_ENABLED = enabled

        status_msg = "activé" if AUTO_MODE_ENABLED else "désactivé"
        app.logger.info(f"Mode automatique {status_msg} par l'API.")
        
        return jsonify({"success": True, "enabled": AUTO_MODE_ENABLED}), 200

    except Exception as e:
        app.logger.error(f"Erreur inattendue lors de la modification du mode automatique: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/force_run_step', methods=['POST'])
def force_run_step():
    """
    Force l'exécution d'une étape spécifique, en contournant les vérifications d'état.
    - Utilisé pour les reprises manuelles ou les tests
    """
    global LAST_SEQUENCE_OUTCOME
    try:
        data = request.get_json()
        step_key = data.get("step_key", None)
        if step_key is None or step_key not in COMMANDS_CONFIG:
            return jsonify({"error": "Clé d'étape invalide."}), 400
        app.logger.info(f"Exécution forcée de l'étape: {step_key}")
        info = process_manager.process_info[step_key]
        info['status'] = 'idle'
        info['log'].clear()
        process_manager.run_process_async(step_key)
        return jsonify({"success": True, "step_key": step_key}), 200
    except Exception as e:
        app.logger.error(f"Erreur inattendue lors de l'exécution forcée de l'étape: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

# --- Routes pour les Tests et le Débogage ---
@app.route('/api/test_logging', methods=['POST'])
def test_logging():
    """
    Teste l'écriture dans les logs de l'application.
    - Attend un message dans la requête JSON
    """
    try:
        data = request.get_json()
        message = data.get("message", "Pas de message fourni")

        app.logger.info(f"Test Logging: {message}")

        return jsonify({"success": True, "message": message}), 200

    except Exception as e:
        app.logger.error(f"Erreur inattendue dans /api/test_logging: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/log_client_error', methods=['POST'])
def log_client_error():
    """Endpoint to log client-side errors sent from the frontend."""
    try:
        error_data = request.json
        if not error_data:
            return jsonify({"error": "No data provided"}), 400

        # Log the error data
        app.logger.error(f"Client Error: {json.dumps(error_data)}")
        return jsonify({"status": "success"}), 200
    except Exception as e:
        app.logger.error(f"Error logging client error: {e}", exc_info=True)
        return jsonify({"error": "Failed to log error"}), 500

@app.route('/api/get_commands_config', methods=['GET'])
def get_commands_config():
    try:
        # Convertir manuellement les objets regex en chaînes
        serializable_config = {}
        for key, value in COMMANDS_CONFIG.items():
            serializable_config[key] = {}
            for k, v in value.items():
                if isinstance(v, re.Pattern):
                    serializable_config[key][k] = str(v)
                else:
                    serializable_config[key][k] = v
        
        return jsonify(serializable_config)
    except Exception as e:
        app.logger.error(f"Error serializing COMMANDS_CONFIG: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_auto_mode_status', methods=['GET'])
def get_auto_mode_status():
    # Return some dummy status data
    return jsonify({"is_any_sequence_running_globally": False}), 200

@app.route('/status/<step>', methods=['GET'])
def get_step_status(step):
    # Return some dummy status data for the step
    return jsonify({"status": "not_started"}), 200

def background_task_manager():
    """
    Gère les tâches en arrière-plan, y compris le nettoyage des processus terminés
    et la gestion des tâches GPU en attente.
    """
    app.logger.info("Démarrage du gestionnaire de tâches en arrière-plan")

    while not APP_STOP_EVENT.is_set():
        try:
            # Vérifier et lancer les tâches GPU en attente
            check_and_launch_pending_gpu_task()

            # Nettoyer les processus terminés
            for step_key, info in process_manager.process_info.items():
                if info['process'] and info['process'].poll() is not None:
                    # Le processus est terminé, mettre à jour l'état
                    return_code = info['process'].returncode
                    info['return_code'] = return_code
                    info['status'] = 'completed' if return_code == 0 else 'failed'

                    # Ajouter un log de fin de tâche
                    info['log'].append(f"Tâche terminée avec le code de retour: {return_code}")

                    app.logger.info(f"Tâche {step_key} terminée (Code: {return_code})")

            # Délai avant la prochaine itération
            time.sleep(5)

        except Exception as e:
            app.logger.error(f"Erreur inattendue dans le gestionnaire de tâches en arrière-plan: {e}", exc_info=True)
            time.sleep(10)  # Délai prolongé en cas d'erreur

# Démarrer le gestionnaire de tâches en arrière-plan dans un thread séparé
background_thread = threading.Thread(target=background_task_manager, daemon=True)
background_thread.start()

# --- Point d'entrée de l'application ---
if __name__ == "__main__":
    # Démarrer Localtunnel dans un thread séparé SI RENDER_REGISTER_URL_ENDPOINT est configuré
    if RENDER_REGISTER_URL_ENDPOINT_ENV and RENDER_REGISTER_TOKEN_ENV:
        app.logger.info("Configuration Localtunnel trouvée, tentative de démarrage.")
        localtunnel_thread = threading.Thread(target=manage_localtunnel_and_register, daemon=True)
        localtunnel_thread.start()
    else:
        app.logger.warning("RENDER_REGISTER_URL_ENDPOINT ou RENDER_REGISTER_TOKEN non configuré. Localtunnel ne sera pas démarré.")

    # Démarrer le gestionnaire de tâches en arrière-plan dans un thread séparé
    # Vous avez déjà cette ligne, c'est juste pour le contexte
    # background_thread = threading.Thread(target=background_task_manager, daemon=True)
    # background_thread.start() # Assurez-vous que background_task_manager est bien défini

    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)