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

REM --- Token Hugging Face (si utilisé par analyze_audio_only8.py) ---
REM set HF_AUTH_TOKEN=votre_token_hugging_face_ici

REM --- Variables spécifiques au téléchargement local ---
set LOCAL_DROPBOX_DOWNLOAD_DIR_ENV=G:\Téléchargements
set LOCAL_DOWNLOAD_API_TOKEN=ABC123XYZ789
REM ^^^ Token pour que Make.com puisse appeler votre app_new.py local

REM --- Variables pour enregistrer l'URL de localtunnel sur le serveur Render ---
REM URL complète de l'endpoint sur votre app_render.py pour enregistrer l'URL du tunnel
set RENDER_REGISTER_URL_ENDPOINT=https://render-signal-server.onrender.com/api/register_local_downloader_url
REM Token secret que app_new.py utilisera pour s'authentifier auprès de app_render.py pour cet enregistrement
set "RENDER_REGISTER_TOKEN=WMmWtia^n6RaUA"
REM ^^^ Ce token doit correspondre à la variable d'environnement REGISTER_LOCAL_URL_TOKEN sur Render.com

REM --- Token pour les communications internes sécurisées (par exemple, pour /api/get_remote_status_summary) ---
set INTERNAL_WORKER_COMMS_TOKEN=VOTRE_TOKEN_SECRET_POUR_COMMUNICATIONS_INTERNES
REM ^^^ Définissez un token secret ici pour sécuriser l'endpoint /api/get_remote_status_summary.

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
echo Lancement du serveur Flask local (app_new.py)...
set PYTHON_EXE="%PYTHON_VENV_EXE_ENV%"
set APP_DIR="%BASE_PATH_SCRIPTS_ENV%\mon_workflow_lanceur_gpu"
set APP_PY="%APP_DIR%\app_new.py"

REM Se positionner dans le dossier de l'application pour que Flask trouve les templates, etc.
pushd %APP_DIR%

REM app_new.py va maintenant gérer le lancement de localtunnel lui-même en subprocess
REM et tentera d'enregistrer son URL auprès du serveur Render.
start "Flask Server + LT Manager (app_new.py)" cmd /k "%PYTHON_EXE% %APP_PY%"

echo Attente du démarrage des services (environ 15-20 secondes pour que Flask démarre et que localtunnel s'initialise et s'enregistre)...
timeout /t 20 /nobreak > nul

echo --- Informations Importantes pour Make.com ---
echo 1. Assurez-vous que votre script local 'app_new.py' a bien démarré et que 'localtunnel' est actif (vérifiez la fenêtre "Flask Server + LT Manager").
echo    Il devrait avoir loggué l'URL localtunnel et tenté de l'enregistrer sur votre serveur Render.
echo.

echo 2. Dans Make.com, le scénario doit d'abord faire un GET à:
echo    https://render-signal-server.onrender.com/api/get_local_downloader_url
echo    (Header: X-API-Token = la valeur de PROCESS_API_TOKEN de votre app_render.py)
echo.

echo 3. Ensuite, Make.com doit utiliser l'URL retournée (localtunnel_url) pour faire un POST à:
echo    [URL_DE_LOCALTUNNEL_RECUPEREE]/api/local_download_dropbox
echo    (Header: X-Local-API-Token = %LOCAL_DOWNLOAD_API_TOKEN%)
echo    (Body JSON: { "dropbox_url": "...", "email_subject": "...", "microsoft_graph_email_id": "..." })
echo ---

echo.
echo Ouverture de l'interface web locale du lanceur de workflow (si Flask tourne sur le port %FLASK_PORT%)...
start http://127.0.0.1:%FLASK_PORT%/

popd
echo.
echo Les serveurs sont lancés en arrière-plan.
echo Pour arrêter:
echo   1. Fermez la fenêtre "Flask Server + LT Manager (app_new.py)". Cela devrait aussi tenter d'arrêter localtunnel proprement.
echo.

echo Appuyez sur une touche pour fermer cette fenêtre de lancement...
pause > nul