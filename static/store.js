// store.js
// Squelette simple pour la gestion d'état centralisée (pattern store)

class Store {
    constructor(initialState = {}) {
        this.state = { ...initialState };
        this.listeners = [];
    }

    getState() {
        return { ...this.state };
    }

    setState(partialState) {
        this.state = { ...this.state, ...partialState };
        this.listeners.forEach(fn => fn(this.getState()));
    }

    subscribe(fn) {
        this.listeners.push(fn);
        return () => {
            this.listeners = this.listeners.filter(l => l !== fn);
        };
    }
}

// Exemple d'usage :
// import store from './store.js';
// store.subscribe(state => { ... });
// store.setState({ isLoading: true });

const store = new Store({
    isLoading: false,
    user: null,
    processInfo: {},
    commandsConfig: {}, // Ajouté pour la config dynamique
    // Ajoutez ici d'autres clés d'état global
});

export default store;
