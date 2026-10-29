import { beforeEach, describe, expect, it } from 'vitest';

import type { GameState } from '../api/types';
import {
  clearSavedGame,
  loadSavedGame,
  SAVED_GAME_KEY,
  saveGame,
} from './storage';

const state: GameState = {
  player_interests: { movies: ['Inception'], music: [], food: [] },
  session_id: '22222222-2222-4222-8222-222222222222',
  state_version: 4,
  stage: 'plan',
  relationships: { mara: 8, jun: 8, theo: 8 },
  clues: [],
  interacted_npcs: ['mara', 'jun', 'theo'],
  applied_event_ids: [],
  plan: null,
  cultural_matches: null,
  score: null,
  ending: null,
};

describe('signed-game storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('persists the state and signed token together', () => {
    expect(saveGame({ state, stateToken: 'v1.signed-token' }, localStorage)).toBe(
      true,
    );

    const loaded = loadSavedGame(localStorage);

    expect(loaded?.stateToken).toBe('v1.signed-token');
    expect(loaded?.state.state_version).toBe(4);
    expect(loaded?.state.interacted_npcs).toEqual(['mara', 'jun', 'theo']);
  });

  it('drops a corrupt save instead of resuming unsigned state', () => {
    localStorage.setItem(SAVED_GAME_KEY, '{not-json');

    expect(loadSavedGame(localStorage)).toBeNull();
    expect(localStorage.getItem(SAVED_GAME_KEY)).toBeNull();
  });

  it('rejects a save without a signed token', () => {
    localStorage.setItem(
      SAVED_GAME_KEY,
      JSON.stringify({ version: 1, state, stateToken: '', savedAt: 1 }),
    );

    expect(loadSavedGame(localStorage)).toBeNull();
    expect(localStorage.getItem(SAVED_GAME_KEY)).toBeNull();
  });

  it('clears the save on restart', () => {
    saveGame({ state, stateToken: 'v1.signed-token' }, localStorage);
    clearSavedGame(localStorage);

    expect(loadSavedGame(localStorage)).toBeNull();
  });
});
