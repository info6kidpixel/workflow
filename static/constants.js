// États des étapes
export const STEP_STATES = {
    IDLE: 'idle',
    RUNNING: 'running',
    COMPLETED: 'completed',
    FAILED: 'failed',
    STARTING: 'starting',
    INITIATED: 'initiated',
    PENDING_GPU: 'pending_gpu'
};

// États GPU
export const GPU_STATES = {
    IN_USE: 'in_use',
    WAITING: 'waiting',
    AVAILABLE: 'available'
};

// Classes CSS pour les états
export const STATE_CLASSES = {
    [STEP_STATES.IDLE]: 'status-idle',
    [STEP_STATES.RUNNING]: 'status-running',
    [STEP_STATES.COMPLETED]: 'status-completed',
    [STEP_STATES.FAILED]: 'status-failed',
    [STEP_STATES.STARTING]: 'status-starting',
    [STEP_STATES.INITIATED]: 'status-initiated',
    [STEP_STATES.PENDING_GPU]: 'status-pending-gpu'
};

// Messages d'état pour l'interface
export const STATUS_MESSAGES = {
    [STEP_STATES.IDLE]: 'En attente',
    [STEP_STATES.RUNNING]: 'En cours',
    [STEP_STATES.COMPLETED]: 'Terminé',
    [STEP_STATES.FAILED]: 'Échoué',
    [STEP_STATES.STARTING]: 'Démarrage...',
    [STEP_STATES.INITIATED]: 'Initié...',
    [STEP_STATES.PENDING_GPU]: 'En attente GPU'
};

// Messages d'état GPU pour l'interface
export const GPU_STATUS_MESSAGES = {
    [GPU_STATES.IN_USE]: 'GPU en utilisation',
    [GPU_STATES.WAITING]: 'En attente du GPU',
    [GPU_STATES.AVAILABLE]: 'GPU disponible'
};
