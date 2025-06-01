import { initCustomSequence } from '../sequenceManager.js';
import store from '../store.js';

describe('sequenceManager.js', () => {
  it('should initialize a custom sequence with config from store', () => {
    store.setState({ commandsConfig: { step1: { cmd: ['echo', 'ok'] } } });
    const seq = initCustomSequence(['step1']);
    expect(seq).toBeDefined();
    expect(seq.steps[0].cmd).toEqual(['echo', 'ok']);
  });
  // Vous pouvez ajouter des tests pour la gestion d'erreur, l'appel API, etc.
});
