@echo off
chcp 65001 > nul 
echo Configuration des variables d'environnement pour le script...
echo Veuillez vous assurer que les chemins et tokens ci-dessous sont corrects.

REM --- Chemins de base et Environnements Python ---
set BASE_PATH_SCRIPTS_ENV=F:\test_mediapipe
set PYTHON_VENV_EXE_ENV=%BASE_PATH_SCRIPTS_ENV%\.venv_audio\Scripts\python.exe
set PYTHON_VENV_TRANSNET_EXE_ENV=%BASE_PATH_SCRIPTS_ENV%\TransNetV2\venv_transnet\Scripts\python.exe

REM --- Dossiers de Logs ---
set AUDIO_ANALYSIS_LOG_DIR_ENV=%BASE_PATH_SCRIPTS_ENV%\logs_audio_tv
set AERENDER_LOGS_DIR_ENV=%BASE_PATH_SCRIPTS_ENV%\logs_watchfolder
set STEP0_PREP_LOG_DIR_ENV=%BASE_PATH_SCRIPTS_ENV%\_MediaSolution_Step1_Logs
set BASE_TRACKING_LOG_SEARCH_PATH_ENV=F:\
set BASE_TRACKING_PROGRESS_SEARCH_PATH_ENV=F:\
set LOCAL_DROPBOX_DOWNLOAD_DIR_ENV=%BASE_PATH_SCRIPTS_ENV%\Dropbox_Downloads_From_Render

REM --- Token Hugging Face (si utilisé par analyze_audio_only8.py) ---
set HF_AUTH_TOKEN=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

REM --- Variables spécifiques au téléchargement local ---
set LOCAL_DOWNLOAD_API_TOKEN=YOUR_SECRET_TOKEN_XYZ789
REM ^^^ Token pour que Make.com puisse appeler votre app_new.py local

REM --- Variables pour enregistrer l'URL de localtunnel sur le serveur Render ---
REM URL complète de l'endpoint sur votre app_render.py pour enregistrer l'URL du tunnel
set RENDER_REGISTER_URL_ENDPOINT=https://render-signal-server.onrender.com/api/register_local_downloader_url
REM Token secret que app_new.py utilisera pour s'authentifier auprès de app_render.py pour cet enregistrement
set RENDER_REGISTER_TOKEN=WMmWtian6RaUA
REM ^^^ Ce token doit correspondre à la variable d'environnement REGISTER_LOCAL_URL_TOKEN sur Render.com

REM --- Token pour la communication interne entre workers ---
set INTERNAL_WORKER_COMMS_TOKEN=YOUR_INTERNAL_WORKER_COMMS_TOKEN

REM --- Configuration du polling distant ---
set REMOTE_TRIGGER_URL=https://render-signal-server.onrender.com/api/check_trigger
set REMOTE_POLLING_INTERVAL=15

REM --- Configuration du Port Flask pour app_new.py ---
set FLASK_PORT=5000

echo.
echo --- Configuration Actuelle (pour vérification) ---
echo BASE_PATH_SCRIPTS_ENV: %BASE_PATH_SCRIPTS_ENV%
echo PYTHON_VENV_EXE_ENV: %PYTHON_VENV_EXE_ENV%
echo LOCAL_DROPBOX_DOWNLOAD_DIR_ENV: %LOCAL_DROPBOX_DOWNLOAD_DIR_ENV%
echo LOCAL_DOWNLOAD_API_TOKEN (premiers 5 chars): %LOCAL_DOWNLOAD_API_TOKEN:~0,5%...
echo RENDER_REGISTER_URL_ENDPOINT: %RENDER_REGISTER_URL_ENDPOINT%
echo RENDER_REGISTER_TOKEN (premiers 5 chars): %RENDER_REGISTER_TOKEN:~0,5%...
echo INTERNAL_WORKER_COMMS_TOKEN (premiers 5 chars): %INTERNAL_WORKER_COMMS_TOKEN:~0,5%...
echo FLASK_PORT: %FLASK_PORT%
echo ---

echo.
echo Démarrage de l'application Flask...
cd %BASE_PATH_SCRIPTS_ENV%\mon_workflow_lanceur_gpu
REM "%PYTHON_VENV_EXE_ENV%" app_new.py <--- L'ancienne ligne

REM Nouvelle section pour lancer Python ET ouvrir le navigateur
REM Lancer l'application Python en arrière-plan pour que le .bat puisse continuer
REM ET ouvrir le navigateur.
echo Lancement de l'application Python en arriere-plan...
start "AppNewPy" /B "%PYTHON_VENV_EXE_ENV%" app_new.py

REM Donner un petit délai pour que le serveur Flask ait le temps de démarrer
echo Attente de quelques secondes pour le demarrage du serveur Flask...
timeout /t 5 /nobreak > nul 
REM Le timeout de 5 secondes est un exemple, ajustez si nécessaire. 
REM '/nobreak' empêche l'utilisateur d'interrompre avec une touche.
REM '> nul' cache la sortie du timeout.

REM Ouvrir l'URL dans le navigateur par défaut
echo Ouverture de l'application dans le navigateur...
start http://127.0.0.1:5000/
REM J'utilise 127.0.0.1 ici car c'est plus universel pour la machine locale.
REM Si vous voulez spécifiquement 192.168.1.135, vous pouvez l'utiliser, mais 
REM cela dépend de la configuration IP de votre machine.

echo.
echo L'application Python devrait etre en cours d'execution en arriere-plan.
echo Le navigateur devrait s'ouvrir sur la page d'accueil.
echo Pour arreter l'application Python, fermez la fenetre de console qui s'est ouverte
echo (celle nommée "AppNewPy" ou la console Python si /B ne la cache pas complètement)
echo ou utilisez Ctrl+C dans la console ou le gestionnaire des tâches.

REM Le script .bat va maintenant se terminer, mais l'application Python continue.
REM La pause n'est plus vraiment nécessaire ici si le navigateur s'ouvre.
REM pause