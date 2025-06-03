import sys
print(f'Python executable: {sys.executable}')
from flask import Flask, render_template, jsonify, request
import contextlib # Pas utilisé directement au niveau global, mais peut-être par des imports ?
import csv # Pas utilisé directement au niveau global
import html # Pas utilisé directement au niveau global
import json
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
from pathlib import Path
from datetime import datetime, timezone, timedelta # timedelta pas utilisé directement
import uuid # Pas utilisé directement au niveau global
import traceback
import os
import threading
import subprocess
import time
import re
import requests
from flask_caching import Cache
from utils import format_duration_seconds # Assurez-vous que utils.py est accessible

REMOTE_SEQUENCE_STEP_KEYS = ["preparation_dezip", "scene_cut", "analyze_audio", "tracking", "minify_json"]

# --- Configuration Globale de l'Application (DÉPLACÉ PLUS HAUT) ---
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
LOCAL_DROPBOX_DOWNLOAD_DIR_ENV = os.environ.get('LOCAL_DROPBOX_DOWNLOAD_DIR_ENV', str(BASE_PATH_SCRIPTS / "Dropbox_Downloads_From_Render"))
LOCAL_DROPBOX_DOWNLOAD_DIR = Path(LOCAL_DROPBOX_DOWNLOAD_DIR_ENV)
LOCAL_DROPBOX_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Default/Reference tokens if not set by environment variables
DEFAULT_HF_TOKEN = "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"
REF_LOCAL_DOWNLOAD_API_TOKEN_NEW = ""
REF_RENDER_REGISTER_TOKEN_NEW = ""
REF_INTERNAL_WORKER_COMMS_TOKEN_NEW = ""

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
        "display_name": "Tracking MediaPipe (Batch Scan)",
        "command": [PYTHON_VENV_EXE, str(BASE_PATH_SCRIPTS / "run_parallel_video_processing_blendshapes_good.py")],
        "gpu_intensive": True,
        "progress_patterns": {
            "total": re.compile(r"TOTAL_TRACKING_JOBS: (\d+)"),
            "current": re.compile(r"Lancements/Exécutions de workers réussis \(code retour 0 du worker\): (\d+)"),
            "progress_text": re.compile(r"\[Gestionnaire\] Préparation : (.*?) \("),
        },
        "specific_logs": False
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
app.logger.addHandler(logger_handler) # Ajouter le handler au logger de Flask
app.logger.setLevel(logging.DEBUG)   # S'assurer que le logger de Flask a le bon niveau

# Custom JSON encoder to handle non-serializable objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, re.Pattern):
            return str(obj)
        if isinstance(obj, Path): # Ajout pour Path si besoin
            return str(obj)
        return super().default(obj)

app.json_encoder = CustomJSONEncoder

# --- Configuration Tokens & Logging (Section consolidée) ---
app.logger.info("--- Initialisation Configuration Tokens ---")

def get_token_with_fallback(env_var_name, ref_value, default_value=None, token_name_for_log="TOKEN"):
    """Centralise la logique de fallback pour les tokens et log la source."""
    value = os.environ.get(env_var_name)
    if value:
        app.logger.info(f"{token_name_for_log}: Défini via variable d'environnement ('...{value[-5:]}' si assez long).")
        return value
    if ref_value: # Note: vos REF_xxx sont des chaînes vides pour l'instant
        app.logger.warning(f"{token_name_for_log}: Non défini en env, fallback sur valeur de référence (qui est '{ref_value}').")
        return ref_value
    if default_value:
        app.logger.warning(f"{token_name_for_log}: Non défini en env ni ref, fallback sur valeur par défaut codée ('...{default_value[-5:]}' si assez long).")
        return default_value
    app.logger.error(f"{token_name_for_log}: Non défini en env, ref, ou défaut. Fallback sur chaîne vide !")
    return ""

HF_AUTH_TOKEN_ENV = get_token_with_fallback("HF_AUTH_TOKEN", None, DEFAULT_HF_TOKEN, "HF_AUTH_TOKEN")
LOCAL_DOWNLOAD_API_TOKEN_ENV = get_token_with_fallback("LOCAL_DOWNLOAD_API_TOKEN", REF_LOCAL_DOWNLOAD_API_TOKEN_NEW, None, "LOCAL_DOWNLOAD_API_TOKEN")
RENDER_APP_CALLBACK_URL_ENV = os.environ.get("RENDER_APP_CALLBACK_URL") # Pas de fallback pour celui-ci
RENDER_APP_CALLBACK_TOKEN_ENV = os.environ.get("RENDER_APP_CALLBACK_TOKEN") # Pas de fallback

RENDER_REGISTER_URL_ENDPOINT_ENV = os.environ.get("RENDER_REGISTER_URL_ENDPOINT")
RENDER_REGISTER_TOKEN_ENV = get_token_with_fallback("RENDER_REGISTER_TOKEN", REF_RENDER_REGISTER_TOKEN_NEW, None, "RENDER_REGISTER_TOKEN")
INTERNAL_WORKER_COMMS_TOKEN_ENV = get_token_with_fallback("INTERNAL_WORKER_COMMS_TOKEN", REF_INTERNAL_WORKER_COMMS_TOKEN_NEW, None, "INTERNAL_WORKER_COMMS_TOKEN")

# Logique de vérification additionnelle après get_token_with_fallback si nécessaire
if not LOCAL_DOWNLOAD_API_TOKEN_ENV or LOCAL_DOWNLOAD_API_TOKEN_ENV == "YOUR_SECRET_TOKEN_FOR_LOCAL_PC": # Ancien placeholder
    app.logger.warning("LOCAL_DOWNLOAD_API_TOKEN: Non défini correctement ou utilise un placeholder! Endpoint de téléchargement local NON SÉCURISÉ.")
if not RENDER_REGISTER_URL_ENDPOINT_ENV or not RENDER_REGISTER_TOKEN_ENV:
    app.logger.warning("RENDER_REGISTER_URL_ENDPOINT ou RENDER_REGISTER_TOKEN: Non configuré. L'URL Localtunnel ne sera pas enregistrée.")
if not INTERNAL_WORKER_COMMS_TOKEN_ENV:
     app.logger.warning("INTERNAL_WORKER_COMMS_TOKEN: Non défini. Endpoint /api/get_remote_status_summary NON SÉCURISÉ.")

app.logger.info("--- Fin Initialisation Configuration Tokens ---")


# --- INITIALISATION DES MANAGERS (DÉPLACÉ PLUS HAUT) ---
from gpu_manager import GPUManager, GpuUnavailableError # Assurez-vous que gpu_manager.py est accessible
from sequence_manager import SequenceManager # Assurez-vous que sequence_manager.py est accessible
from process_manager import ProcessManager # Assurez-vous que process_manager.py est accessible

APP_STOP_EVENT = threading.Event()

gpu_manager = GPUManager(logger=app.logger, wait_timeout=300)
if hasattr(gpu_manager, 'set_commands_config'):
    gpu_manager.set_commands_config(COMMANDS_CONFIG)
if hasattr(gpu_manager, 'set_app_stop_event'):
    gpu_manager.set_app_stop_event(APP_STOP_EVENT)

process_manager = ProcessManager(config=COMMANDS_CONFIG, logger=app.logger, gpu_manager=gpu_manager)
sequence_manager = SequenceManager(process_manager=process_manager, logger=app.logger)
# --- FIN INITIALISATION DES MANAGERS ---


# URL Localtunnel active
LOCALTUNNEL_URL = None # Renommé LT_URL en LOCALTUNNEL_URL pour cohérence
LT_URL_LOCK = threading.Lock() # Renommé LT_URL_LOCK pour cohérence

# Autres variables globales
LOG_BASE_DIRECTORY_VIDER_CACHE = r'F:\test_mediapipe\log_vide_cache'
LOG_FILENAME_PREFIX_VIDER_CACHE = 'cache_cleanup_log'
LOG_FILE_EXTENSION_VIDER_CACHE = '.txt'

ACTIVE_LOCAL_DOWNLOADS = {}
KEPT_DOWNLOAD_STATUSES_DEQUE = deque(maxlen=20)
LOCAL_DOWNLOADS_LOCK = threading.Lock()

AUTO_MODE_ENABLED = True
AUTO_MODE_LOCK = threading.Lock() # Utilisé ?
AUTO_MODE_TRIGGER_QUEUE = deque() # Utilisé ?
AUTO_MODE_QUEUE_LOCK = threading.Lock() # Utilisé ?
# CURRENT_AUTO_MODE_ACTIVE_STEP_KEY est géré par sequence_manager

LAST_SEQUENCE_OUTCOME = {"status": "never_run", "timestamp": None, "type": "N/A"} # Initialisation plus complète
# Cette variable globale est aussi gérée par sequence_manager.set_last_outcome,
# il faudrait peut-être centraliser sa lecture/écriture via le manager.


REMOTE_TRIGGER_URL_ENV = os.environ.get('REMOTE_TRIGGER_URL', "https://render-signal-server.onrender.com/api/check_trigger")
REMOTE_TRIGGER_URL = REMOTE_TRIGGER_URL_ENV # Est-ce nécessaire d'avoir les deux ?
REMOTE_POLLING_INTERVAL = int(os.environ.get('REMOTE_POLLING_INTERVAL', "15"))
# REMOTE_SEQUENCE_STEP_KEYS = ["preparation_dezip", "scene_cut", "analyze_audio", "tracking", "minify_json"] # Utilisé ?
# is_currently_running_any_sequence est géré par sequence_manager
# sequence_lock est géré par sequence_manager

# Configuration du cache
CACHE_CONFIG = { "CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": 300 }
app.config.from_mapping(CACHE_CONFIG)
cache = Cache(app)

# Journalisation des exceptions non gérées
def log_uncaught_exceptions(ex_cls, ex, tb_log): # Renommé tb en tb_log pour éviter conflit
    app.logger.critical(''.join(traceback.format_tb(tb_log)))
    app.logger.critical('{0}: {1}'.format(ex_cls, ex))
sys.excepthook = log_uncaught_exceptions


# --- Définition des routes Flask ---
@app.route('/')
def index():
    localtunnel_active_url = get_localtunnel_url()
    return render_template('index_new.html',
                           localtunnel_url=localtunnel_active_url,
                           steps_config=COMMANDS_CONFIG)

@app.route('/cancel/<step_key>', methods=['POST'])
def cancel_step(step_key):
    # La logique de cancel_step dans ProcessManager semble prendre current_auto_mode_key
    # qui vient de sequence_manager.
    current_auto_key = sequence_manager.get_current_auto_mode_key()
    with sequence_manager.lock(): # Assurer la cohérence d'état
        # Si aucune séquence n'est en cours, on ne peut pas annuler une étape "de séquence"
        # Mais on pourrait vouloir annuler une étape manuelle lancée hors séquence ?
        # La logique actuelle de ProcessManager.cancel_step se base sur get_active_step_key
        # qui peut trouver une étape active même hors séquence.
        # if not sequence_manager.is_running():
        #     return jsonify({"success": False, "message": "Aucune séquence en cours pour annulation."}), 400

        success, actual_step_key, error_msg = process_manager.cancel_step(step_key, current_auto_key)

        if not success:
            return jsonify({"success": False, "message": error_msg or "Erreur lors de l'annulation."}), 400

        # Si l'annulation a réussi et que cela faisait partie d'une séquence
        if sequence_manager.is_running() and actual_step_key == current_auto_key : # ou actual_step_key in sequence_manager.current_sequence_steps:
            sequence_manager.stop_requested = True # Indiquer à la séquence de s'arrêter
            sequence_manager.update_last_sequence_outcome("canceled", f"Séquence annulée manuellement à l'étape {actual_step_key}")
            # sequence_manager.set_current_auto_mode_key(None) # Fait par le worker de sequence_manager

        info = process_manager.process_info.get(actual_step_key, {}) # .get pour éviter KeyError si actual_step_key est None
        return jsonify({
            "success": True,
            "step_key": actual_step_key,
            "status": info.get('status', 'unknown'),
            "log": list(info.get('log', []))
        }), 200


@app.route('/api/get_remote_status_summary', methods=['GET'])
def get_remote_status_summary():
    global REMOTE_TRIGGER_URL_ENV # Utiliser la variable déjà chargée
    try:
        if not REMOTE_TRIGGER_URL_ENV:
            return jsonify({"error": "URL de déclenchement distante non configurée."}), 500
        response = requests.get(REMOTE_TRIGGER_URL_ENV, timeout=10)
        response.raise_for_status()
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
        app.logger.error(f"Erreur inattendue dans get_remote_status_summary: {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/trigger_render_sequence', methods=['POST'])
def trigger_render_sequence():
    global REMOTE_TRIGGER_URL_ENV
    try:
        if not REMOTE_TRIGGER_URL_ENV:
            return jsonify({"error": "URL de déclenchement distante non configurée."}), 500
        data = request.get_json()
        steps_to_run = data.get("steps", [])
        app.logger.info(f"Reçu demande de déclenchement pour les étapes distantes: {steps_to_run}")
        if not isinstance(steps_to_run, list) or not all(isinstance(step, str) for step in steps_to_run):
            return jsonify({"error": "Données de demande invalides."}), 400
        response = requests.post(REMOTE_TRIGGER_URL_ENV, json={"steps": steps_to_run}, timeout=10)
        response.raise_for_status()
        result = response.json()
        app.logger.info(f"Résultat de la soumission distante: {result}")
        return jsonify(result), 200
    except requests.exceptions.Timeout: # Répétition de la gestion d'erreur, pourrait être factorisée
        app.logger.error("Délai d'attente dépassé (trigger_render_sequence).")
        return jsonify({"error": "Délai d'attente dépassé."}), 504
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erreur RequestException (trigger_render_sequence): {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error(f"Erreur inattendue (trigger_render_sequence): {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/cancel_render_sequence', methods=['POST'])
def cancel_render_sequence():
    global REMOTE_TRIGGER_URL_ENV
    try:
        if not REMOTE_TRIGGER_URL_ENV:
            return jsonify({"error": "URL de déclenchement distante non configurée."}), 500
        response = requests.post(f"{REMOTE_TRIGGER_URL_ENV}/cancel", timeout=10)
        response.raise_for_status()
        result = response.json()
        app.logger.info(f"Résultat de l'annulation distante: {result}")
        return jsonify(result), 200
    except requests.exceptions.Timeout: # Répétition
        app.logger.error("Délai d'attente dépassé (cancel_render_sequence).")
        return jsonify({"error": "Délai d'attente dépassé."}), 504
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Erreur RequestException (cancel_render_sequence): {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error(f"Erreur inattendue (cancel_render_sequence): {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/get_process_info', methods=['GET'])
def get_process_info():
    try:
        process_summary = process_manager.get_process_info_summary()
        return jsonify(process_summary), 200
    except Exception as e:
        app.logger.error(f"Erreur inattendue (get_process_info): {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/get_config', methods=['GET'])
def get_config_api(): # Renommé pour éviter conflit avec variable `config` potentielle
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
                "enabled": AUTO_MODE_ENABLED, # Cette globale est-elle toujours utilisée ?
                "current_active_step": sequence_manager.get_current_auto_mode_key()
            },
            "last_sequence_outcome": sequence_manager.get_last_outcome()
        }
        return jsonify(config_safe), 200
    except Exception as e:
        app.logger.error(f"Erreur inattendue (get_config_api): {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/set_auto_mode', methods=['POST'])
def set_auto_mode():
    global AUTO_MODE_ENABLED # Si cette globale est toujours pertinente
    try:
        data = request.get_json()
        enabled = data.get("enabled") # Pas de valeur par défaut None, pour attraper l'erreur si manquant
        if enabled is None:
            return jsonify({"error": "Champ 'enabled' manquant."}), 400
        if not isinstance(enabled, bool):
            return jsonify({"error": "Champ 'enabled' doit être un booléen."}), 400

        AUTO_MODE_ENABLED = enabled
        status_msg = "activé" if AUTO_MODE_ENABLED else "désactivé"
        app.logger.info(f"Mode automatique {status_msg} par l'API.")
        return jsonify({"success": True, "enabled": AUTO_MODE_ENABLED}), 200
    except Exception as e:
        app.logger.error(f"Erreur inattendue (set_auto_mode): {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/force_run_step', methods=['POST'])
def force_run_step():
    try:
        data = request.get_json()
        step_key = data.get("step_key")
        if step_key is None or step_key not in COMMANDS_CONFIG:
            return jsonify({"error": "Clé d'étape invalide ou manquante."}), 400

        # Vérifier si une séquence est déjà en cours pour éviter les conflits
        if sequence_manager.is_running():
            return jsonify({"error": f"Impossible de forcer l'étape '{step_key}', une séquence est déjà en cours (étape: {sequence_manager.get_current_auto_mode_key()})."}), 409 # Conflict

        app.logger.info(f"Exécution forcée de l'étape: {step_key} (demandée par API)")
        # La logique de process_manager.run_process_async réinitialise déjà l'état
        process_manager.run_process_async(step_key, is_auto_mode_step=False, sequence_type="ForcedManual")
        return jsonify({"success": True, "step_key": step_key, "message": f"Lancement forcé de {step_key} initié."}), 202 # Accepted
    except Exception as e:
        app.logger.error(f"Erreur inattendue (force_run_step): {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/test_logging', methods=['POST'])
def test_logging():
    try:
        data = request.get_json()
        message = data.get("message", "Pas de message fourni pour test_logging")
        app.logger.info(f"API Test Logging: {message}")
        return jsonify({"success": True, "message_logged": message}), 200
    except Exception as e:
        app.logger.error(f"Erreur inattendue (/api/test_logging): {e}", exc_info=True)
        return jsonify({"error": "Erreur inattendue"}), 500

@app.route('/api/log_client_error', methods=['POST'])
def log_client_error():
    try:
        error_data = request.json
        if not error_data:
            return jsonify({"error": "No data provided"}), 400
        app.logger.error(f"CLIENT SIDE ERROR: {json.dumps(error_data)}")
        return jsonify({"status": "success", "message": "Client error logged."}), 200
    except Exception as e:
        app.logger.error(f"Error in /api/log_client_error: {e}", exc_info=True)
        return jsonify({"error": "Failed to log client error"}), 500

@app.route('/api/get_commands_config', methods=['GET'])
def get_commands_config_api(): # Renommé
    try:
        # COMMANDS_CONFIG est déjà sérialisable grâce à CustomJSONEncoder pour les regex
        # et Path si ajouté. Si ce n'est pas le cas, il faut le faire ici.
        return jsonify(COMMANDS_CONFIG)
    except Exception as e:
        app.logger.error(f"Error serializing COMMANDS_CONFIG for API: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_auto_mode_status', methods=['GET']) # Pourrait être fusionné dans /api/get_config
def get_auto_mode_status():
    return jsonify({
        "is_auto_mode_enabled_globally": AUTO_MODE_ENABLED, # Si AUTO_MODE_ENABLED est la source de vérité
        "is_any_sequence_running": sequence_manager.is_running(),
        "current_auto_mode_step": sequence_manager.get_current_auto_mode_key(),
        "last_sequence_outcome": sequence_manager.get_last_outcome()
    }), 200

@app.route('/status/<step>', methods=['GET']) # Route simple, peut-être pour des checks externes basiques
def get_step_status(step):
    if step in process_manager.process_info:
        info = process_manager.process_info[step]
        return jsonify({
            "step_key": step,
            "status": info['status'],
            "progress_current": info['progress_current'],
            "progress_total": info['progress_total'],
        }), 200
    return jsonify({"error": "Step not found"}), 404


# --- Fonctions Utilitaires (si elles ne sont pas dans utils.py) ---
def create_frontend_safe_config(config_dict: dict) -> dict: # Semble redondant si CustomJSONEncoder gère Path et re.Pattern
    frontend_config = {}
    for step_key, step_data_orig in config_dict.items():
        # ... (logique existante, mais vérifier si c'est encore nécessaire)
        pass # Pour l'instant, on suppose que le JSONEncoder suffit.
    return config_dict # ou frontend_config si la logique est réactivée

def sanitize_filename_local(filename_str, max_length=230):
    # ... (logique existante)
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


# --- Gestion Localtunnel ---
LT_PROCESS = None # Garder une référence globale au processus LT
def get_localtunnel_url():
    global LOCALTUNNEL_URL
    with LT_URL_LOCK:
        return LOCALTUNNEL_URL

def set_localtunnel_url(url):
    global LOCALTUNNEL_URL
    with LT_URL_LOCK:
        LOCALTUNNEL_URL = url
    if url: app.logger.info(f"LOCALTUNNEL_MGR: URL Localtunnel active mise à jour à: {url}")
    else: app.logger.info("LOCALTUNNEL_MGR: URL Localtunnel désactivée (None).")

def try_unregister_url(url_to_unregister): # Renommé pour clarté
    if not url_to_unregister:
        app.logger.warning("try_unregister_url: URL vide, désenregistrement ignoré.")
        return False
    if not RENDER_REGISTER_URL_ENDPOINT_ENV or not RENDER_REGISTER_TOKEN_ENV:
        app.logger.warning("try_unregister_url: Configuration Render manquante pour désenregistrement.")
        return False
    try:
        payload = {"localtunnel_url": None, "timestamp": datetime.now(timezone.utc).isoformat(), "previous_url": url_to_unregister}
        headers = {"X-Register-Token": RENDER_REGISTER_TOKEN_ENV, "Content-Type": "application/json"}
        response = requests.post(RENDER_REGISTER_URL_ENDPOINT_ENV, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            app.logger.info(f"URL {url_to_unregister} désenregistrée avec succès.")
            return True
        app.logger.warning(f"Échec désenregistrement URL {url_to_unregister} - Status: {response.status_code}, Réponse: {response.text[:200]}")
        return False
    except Exception as e:
        app.logger.error(f"Erreur lors du désenregistrement de l'URL {url_to_unregister}: {e}", exc_info=True)
        return False

def find_localtunnel_executable():
    # ... (logique existante)
    npm_global_path_str = os.path.join(os.environ.get('APPDATA', ''), 'npm')
    paths_to_check = [
        os.path.join(npm_global_path_str, "lt.cmd"),
        "lt.cmd",                                  
        "lt",                                      
    ]
    app.logger.debug(f"LOCALTUNNEL_MGR: Chemins de recherche pour lt: {paths_to_check}")
    for p_candidate_str in paths_to_check:
        try:
            if os.path.isabs(p_candidate_str):
                if os.path.isfile(p_candidate_str):
                    app.logger.info(f"LOCALTUNNEL_MGR: Exécutable trouvé (absolu): {p_candidate_str}")
                    return p_candidate_str
                continue
            cmd_to_try = [p_candidate_str, "--version"]
            app.logger.debug(f"LOCALTUNNEL_MGR: Tentative via PATH: {' '.join(cmd_to_try)}")
            process = subprocess.Popen(cmd_to_try, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            stdout, stderr = process.communicate(timeout=5)
            if process.returncode == 0:
                app.logger.info(f"LOCALTUNNEL_MGR: Exécutable '{p_candidate_str}' trouvé via PATH.")
                return p_candidate_str
        except Exception as e: # Simplifié pour concision, l'original était plus détaillé
            app.logger.debug(f"LOCALTUNNEL_MGR: Erreur ou non trouvé pour '{p_candidate_str}': {e}")
    app.logger.error("LOCALTUNNEL_MGR: Exécutable 'lt' ou 'lt.cmd' NON TROUVÉ.")
    return None


def register_localtunnel_url_external(new_url): # Renommé pour éviter conflit
    if not (RENDER_REGISTER_URL_ENDPOINT_ENV and RENDER_REGISTER_TOKEN_ENV):
        app.logger.info(f"LOCALTUNNEL_MGR: URL {new_url} obtenue mais pas d'enregistrement configuré.")
        return True # Considéré comme succès car pas d'action requise
    try:
        payload = {"localtunnel_url": new_url, "timestamp": datetime.now(timezone.utc).isoformat()}
        headers = {"X-Register-Token": RENDER_REGISTER_TOKEN_ENV, "Content-Type": "application/json"}
        response = requests.post(RENDER_REGISTER_URL_ENDPOINT_ENV, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            app.logger.info(f"LOCALTUNNEL_MGR: URL {new_url} enregistrée avec succès sur {RENDER_REGISTER_URL_ENDPOINT_ENV}.")
            return True
        app.logger.error(f"LOCALTUNNEL_MGR: Échec enregistrement URL {new_url} - Status: {response.status_code}, Réponse: {response.text[:200]}")
        return False
    except Exception as e:
        app.logger.error(f"LOCALTUNNEL_MGR: Erreur lors de l'enregistrement de l'URL: {e}", exc_info=True)
        return False

def cleanup_localtunnel_process(process_to_clean): # Renommé
    if process_to_clean and process_to_clean.poll() is None:
        app.logger.info("LOCALTUNNEL_MGR: Tentative d'arrêt du processus LT...")
        try:
            process_to_clean.terminate()
            process_to_clean.wait(timeout=5)
            app.logger.info("LOCALTUNNEL_MGR: Processus LT terminé (terminate).")
            return True
        except subprocess.TimeoutExpired:
            app.logger.warning("LOCALTUNNEL_MGR: Timeout (terminate), tentative kill...")
            process_to_clean.kill()
            process_to_clean.wait(timeout=5) # Attendre après kill
            app.logger.info("LOCALTUNNEL_MGR: Processus LT terminé (kill).")
            return True
        except Exception as e:
            app.logger.error(f"LOCALTUNNEL_MGR: Erreur nettoyage processus LT: {e}", exc_info=True)
    return True # Si déjà terminé ou None

def manage_localtunnel_and_register():
    global LT_PROCESS # Utiliser la variable globale
    consecutive_failures = 0
    current_lt_url_local_scope = None # Variable locale au thread

    while not APP_STOP_EVENT.is_set():
        try:
            lt_exe_path = find_localtunnel_executable()
            if not lt_exe_path:
                raise FileNotFoundError("localtunnel non trouvé.")

            app.logger.info(f"LOCALTUNNEL_MGR: Démarrage LT avec: {lt_exe_path} pour port 5000")
            cmd = [lt_exe_path, "--port", "5000"]
            LT_PROCESS = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            app.logger.info(f"LOCALTUNNEL_MGR: Processus LT démarré (PID: {LT_PROCESS.pid})")

            for line in iter(LT_PROCESS.stdout.readline, ''): # Lire jusqu'à la fin
                if APP_STOP_EVENT.is_set(): break
                line = line.strip()
                if not line: continue
                app.logger.debug(f"LOCALTUNNEL_OUT: {line}")
                if "your url is:" in line.lower():
                    new_url_candidate = line.split("is:")[-1].strip()
                    if new_url_candidate and new_url_candidate != current_lt_url_local_scope:
                        if current_lt_url_local_scope:
                            try_unregister_url(current_lt_url_local_scope)
                        if register_localtunnel_url_external(new_url_candidate):
                            current_lt_url_local_scope = new_url_candidate
                            set_localtunnel_url(current_lt_url_local_scope) # Mettre à jour la globale
                            consecutive_failures = 0
                        else: # Échec de l'enregistrement
                            app.logger.error("LOCALTUNNEL_MGR: Échec de l'enregistrement, LT va probablement redémarrer.")
                            cleanup_localtunnel_process(LT_PROCESS) # Tuer LT pour forcer redémarrage
                            break # Sortir de la boucle de lecture stdout pour redémarrer
            
            # Si on sort de la boucle stdout (processus terminé ou APP_STOP_EVENT)
            if LT_PROCESS: LT_PROCESS.wait() # S'assurer qu'il est bien terminé
            return_code = LT_PROCESS.returncode if LT_PROCESS else -1
            app.logger.warning(f"LOCALTUNNEL_MGR: Processus LT terminé (code: {return_code})")
            if return_code != 0 and not APP_STOP_EVENT.is_set(): # Sauf si c'est un arrêt normal ou demandé
                 consecutive_failures += 1

        except FileNotFoundError as e_fnf:
            app.logger.error(f"LOCALTUNNEL_MGR: {str(e_fnf)}. Localtunnel ne peut pas démarrer.")
            APP_STOP_EVENT.wait(60) # Attendre plus longtemps si lt n'est pas trouvé
            consecutive_failures += 1
        except Exception as e_manage:
            app.logger.error(f"LOCALTUNNEL_MGR: Erreur inattendue: {str(e_manage)}", exc_info=True)
            consecutive_failures += 1
        finally:
            cleanup_localtunnel_process(LT_PROCESS) # Nettoyer au cas où
            LT_PROCESS = None
            if current_lt_url_local_scope: # Si une URL était active
                try_unregister_url(current_lt_url_local_scope)
                current_lt_url_local_scope = None
                set_localtunnel_url(None) # Mettre à jour la globale
            
            if not APP_STOP_EVENT.is_set():
                delay = min(15 * (2 ** min(consecutive_failures, 5)), 300) # Limiter l'exponentiel
                app.logger.info(f"LOCALTUNNEL_MGR: Attente de {delay}s avant relance (échecs: {consecutive_failures}).")
                APP_STOP_EVENT.wait(delay)
    app.logger.info("LOCALTUNNEL_MGR: Thread de gestion de Localtunnel terminé.")


def background_task_manager_and_gpu_checks():
    """Thread de fond pour gérer les tâches en attente et vérifier l'état du GPU."""
    app.logger.info("BG_THREAD: Démarrage du gestionnaire de tâches en arrière-plan et GPU.")
    while not APP_STOP_EVENT.is_set():
        try:
            # Vérifier et lancer les tâches GPU en attente
            check_and_launch_pending_gpu_task()
            
            # Attente interruptible
            APP_STOP_EVENT.wait(5)
        except Exception as e_bg:
            app.logger.error(f"BG_THREAD: Erreur inattendue: {e_bg}", exc_info=True)
            APP_STOP_EVENT.wait(10)  # Délai plus long en cas d'erreur
    app.logger.info("BG_THREAD: Thread de tâches de fond terminé.")

def check_and_launch_pending_gpu_task():
    """
    Vérifie et lance la prochaine tâche GPU en attente.
    Cette fonction est appelée par le thread de fond ou après qu'une session GPU est libérée.
    """
    try:
        # Vérifier si une séquence est en cours
        current_auto_mode_key = sequence_manager.get_current_auto_mode_key()
        
        # Vérifier si le GPU est disponible
        with gpu_manager._gpu_lock:
            if gpu_manager._gpu_in_use_by is not None:
                app.logger.debug(f"GPU: GPU déjà utilisé par '{gpu_manager._gpu_in_use_by}', pas de lancement de tâche en attente")
                return False
                
            # Chercher une tâche en attente du GPU
            pending_gpu_step = None
            
            # Si une tâche auto_mode est en attente, elle est prioritaire
            if current_auto_mode_key and current_auto_mode_key in process_manager.process_info:
                info = process_manager.process_info[current_auto_mode_key]
                if info['status'] == 'pending_gpu' and COMMANDS_CONFIG.get(current_auto_mode_key, {}).get('gpu_intensive', False):
                    pending_gpu_step = current_auto_mode_key
            
            # Sinon, chercher la première tâche en attente
            if not pending_gpu_step:
                for step_key in REMOTE_SEQUENCE_STEP_KEYS:
                    if step_key in process_manager.process_info and process_manager.process_info[step_key]['status'] == 'pending_gpu':
                        # Vérifier que c'est bien une tâche GPU
                        if COMMANDS_CONFIG.get(step_key, {}).get('gpu_intensive', False):
                            pending_gpu_step = step_key
                            break
                        else:
                            # Incohérence: tâche non-GPU marquée comme pending_gpu
                            app.logger.error(f"Incohérence: {step_key} est marqué pending_gpu mais n'est pas une tâche GPU")
                            process_manager.process_info[step_key]['status'] = 'failed'
                            process_manager.process_info[step_key]['log'].append("Erreur: État incohérent (pending_gpu pour tâche non-GPU)")
            
            if not pending_gpu_step:
                return False
                
            app.logger.info(f"GPU: Lancement de la tâche en attente '{pending_gpu_step}'")
            
        # Lancer la tâche en dehors du lock pour éviter les deadlocks
        try:
            is_auto_mode = pending_gpu_step == current_auto_mode_key
            process_manager.run_process_async(
                pending_gpu_step, 
                is_auto_mode_step=is_auto_mode,
                sequence_type="AutoMode" if is_auto_mode else "Manual"
            )
            return True
        except Exception as e:
            app.logger.error(f"GPU: Erreur lors du lancement de la tâche en attente '{pending_gpu_step}': {e}", exc_info=True)
            process_manager.process_info[pending_gpu_step]['status'] = 'failed'
            process_manager.process_info[pending_gpu_step]['log'].append(f"Erreur lors du lancement: {str(e)}")
            return False
            
    except Exception as e:
        app.logger.error(f"GPU: Erreur inattendue dans check_and_launch_pending_gpu_task: {e}", exc_info=True)
        return False

# --- Point d'entrée de l'application ---
if __name__ == "__main__":
    if RENDER_REGISTER_URL_ENDPOINT_ENV and RENDER_REGISTER_TOKEN_ENV:
        app.logger.info("MAIN: Configuration Localtunnel trouvée, démarrage du thread LT.")
        localtunnel_thread = threading.Thread(target=manage_localtunnel_and_register, daemon=True, name="LocaltunnelThread")
        localtunnel_thread.start()
    else:
        app.logger.warning("MAIN: RENDER_REGISTER_URL_ENDPOINT ou RENDER_REGISTER_TOKEN non configuré. Localtunnel ne sera pas démarré.")

    background_thread = threading.Thread(target=background_task_manager_and_gpu_checks, daemon=True, name="BackgroundTaskThread")
    background_thread.start() # Si vous avez des tâches de fond à gérer ici

    # Récupérer le port depuis les variables d'environnement ou utiliser 5000 par défaut
    flask_port = int(os.environ.get('FLASK_PORT', 5000))
    app.logger.info(f"MAIN: Démarrage du serveur Flask sur 0.0.0.0:{flask_port}")
    app.run(host="0.0.0.0", port=flask_port, debug=False, threaded=True)

    # Code après app.run() ne sera exécuté qu'à l'arrêt du serveur Flask (ex: Ctrl+C)
    app.logger.info("MAIN: Serveur Flask arrêté. Signalisation d'arrêt aux threads.")
    APP_STOP_EVENT.set() # Signaler aux threads de s'arrêter

    # Attendre que les threads se terminent (optionnel, mais propre)
    if 'localtunnel_thread' in locals() and localtunnel_thread.is_alive():
        app.logger.info("MAIN: Attente de la fin du thread Localtunnel...")
        localtunnel_thread.join(timeout=10)
    if 'background_thread' in locals() and background_thread.is_alive():
        app.logger.info("MAIN: Attente de la fin du thread de fond...")
        background_thread.join(timeout=5)
    
    # Unregister LT URL one last time if it was active
    active_lt_url = get_localtunnel_url()
    if active_lt_url:
        app.logger.info(f"MAIN: Tentative de désenregistrement final de l'URL LT: {active_lt_url}")
        try_unregister_url(active_lt_url)

    app.logger.info("MAIN: Application terminée.")
