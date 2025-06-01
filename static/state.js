const initialProcessInfo = {};
document.querySelectorAll('.step').forEach(s => {
    initialProcessInfo[s.dataset.stepKey] = {
        status: 'idle',
        log: [],
        progress_current: 0,
        progress_total: 0,
        progress_text: '',
        is_any_sequence_running: false 
    };
});
if (!initialProcessInfo['clear_disk_cache']) {
    initialProcessInfo['clear_disk_cache'] = {
        status: 'idle', log: [], progress_current: 0, progress_total: 0, progress_text: '',
        is_any_sequence_running: false
    };
}


export const PROCESS_INFO_CLIENT = initialProcessInfo;
export let pollingIntervals = {};
export let activeStepKeyForLogsPanel = null;
export let trackingProgressInterval = null;
export let stepTimers = {};
export let selectedStepsOrder = [];
export let isAnySequenceRunning = false; 
export let focusedElementBeforePopup = null;
export let autoModeEnabled = false;

// NOUVEL ÉTAT POUR SAVOIR SI LE PANNEAU DE LOG A ÉTÉ OUVERT PAR LE MODE AUTO
export let autoModeLogPanelOpened = false; 

// Flag pour suivre si l'utilisateur a manuellement fermé le panneau de logs actifs
export let userManuallyClosedActiveLogPanel = false;

// Constante pour les étapes de la séquence auto (dupliquée de app_new.py pour accès facile)
export const REMOTE_SEQUENCE_STEP_KEYS = ["preparation_dezip", "scene_cut", "analyze_audio", "tracking", "minify_json"];


// Functions to modify state
export function setActiveStepKeyForLogs(key) {
    activeStepKeyForLogsPanel = key;
}
export function getActiveStepKeyForLogs() { // Getter pour activeStepKeyForLogsPanel
    return activeStepKeyForLogsPanel;
}
export function setTrackingProgressInterval(id) {
    if (trackingProgressInterval) clearInterval(trackingProgressInterval);
    trackingProgressInterval = id;
}
export function clearTrackingProgressInterval() {
    if (trackingProgressInterval) clearInterval(trackingProgressInterval);
    trackingProgressInterval = null;
}
export function addStepTimer(stepKey, timerData) {
    stepTimers[stepKey] = timerData;
}
export function getStepTimer(stepKey) {
    return stepTimers[stepKey];
}
export function clearStepTimerInterval(stepKey) {
    if (stepTimers[stepKey] && stepTimers[stepKey].intervalId) {
        clearInterval(stepTimers[stepKey].intervalId);
        stepTimers[stepKey].intervalId = null;
    }
}
export function deleteStepTimer(stepKey) {
    if (stepTimers[stepKey]) {
        clearStepTimerInterval(stepKey);
        delete stepTimers[stepKey];
    }
}
export function setSelectedStepsOrder(order) {
    selectedStepsOrder = order;
}
export function getSelectedStepsOrder() {
    return selectedStepsOrder;
}
export function setIsAnySequenceRunning(running) {
    isAnySequenceRunning = running;
}
export function getIsAnySequenceRunning() {
    return isAnySequenceRunning;
}
export function setFocusedElementBeforePopup(element) {
    focusedElementBeforePopup = element;
}
export function getFocusedElementBeforePopup() {
    return focusedElementBeforePopup;
}
export function addPollingInterval(stepKey, id) {
    pollingIntervals[stepKey] = id;
}
export function clearPollingInterval(stepKey) {
    if (pollingIntervals[stepKey]) {
        clearInterval(pollingIntervals[stepKey]);
        delete pollingIntervals[stepKey];
    }
}
export function getPollingInterval(stepKey) {
    return pollingIntervals[stepKey];
}

export function setAutoModeEnabled(enabled) {
    autoModeEnabled = enabled;
}
export function getAutoModeEnabled() {
    return autoModeEnabled;
}

// NOUVEAUX GETTER/SETTER POUR autoModeLogPanelOpened
export function setAutoModeLogPanelOpened(opened) {
    autoModeLogPanelOpened = opened;
}
export function getAutoModeLogPanelOpened() {
    return autoModeLogPanelOpened;
}

// GETTER/SETTER POUR userManuallyClosedActiveLogPanel
export function setUserManuallyClosedActiveLogPanel(closed) {
    userManuallyClosedActiveLogPanel = closed;
}
export function getUserManuallyClosedActiveLogPanel() {
    return userManuallyClosedActiveLogPanel;
}