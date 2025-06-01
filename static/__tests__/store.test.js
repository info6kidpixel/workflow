// Squelette de test frontend avec Jest (à placer dans static/__tests__/store.test.js)
import store from '../store.js';

describe('store.js', () => {
  it('should set and get state', () => {
    store.setState({ foo: 42 });
    expect(store.getState().foo).toBe(42);
  });

  it('should update state immutably', () => {
    const prev = store.getState();
    store.setState({ bar: 'baz' });
    expect(store.getState()).not.toBe(prev);
    expect(store.getState().bar).toBe('baz');
  });
});

// Pour lancer : npx jest static/__tests__/store.test.js
