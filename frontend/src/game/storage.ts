import type { GameStage, GameState, PlanEvaluateResponse } from '../api/types';

export const SAVED_GAME_KEY = 'tasteverse.signed-game.v1';
const SAVE_VERSION = 1;

export interface SavedGame {
  state: GameState;
  stateToken: string;
  /** Present after a completed plan evaluation so the ending can be resumed. */
  evaluation?: PlanEvaluateResponse;
  savedAt: number;
}

interface StoredSave extends SavedGame {
  version: number;
}

const STAGES: ReadonlySet<GameStage> = new Set(['explore', 'plan', 'complete']);

function defaultStorage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object';
}

function isGameStateLike(value: unknown): value is GameState {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.session_id === 'string' &&
    value.session_id.length > 0 &&
    typeof value.state_version === 'number' &&
    typeof value.stage === 'string' &&
    STAGES.has(value.stage as GameStage) &&
    isRecord(value.player_interests) &&
    Array.isArray(value.interacted_npcs) &&
    isRecord(value.relationships)
  );
}

function parseSave(raw: string): SavedGame | null {
  let parsed: unknown;

  try {
    parsed = JSON.parse(raw) as unknown;
  } catch {
    return null;
  }

  if (!isRecord(parsed) || parsed.version !== SAVE_VERSION) {
    return null;
  }

  if (
    !isGameStateLike(parsed.state) ||
    typeof parsed.stateToken !== 'string' ||
    parsed.stateToken.length === 0
  ) {
    return null;
  }

  const save: SavedGame = {
    state: parsed.state,
    stateToken: parsed.stateToken,
    savedAt:
      typeof parsed.savedAt === 'number' && Number.isFinite(parsed.savedAt)
        ? parsed.savedAt
        : Date.now(),
  };

  if (isRecord(parsed.evaluation)) {
    const evaluation = parsed.evaluation as unknown as PlanEvaluateResponse;

    if (
      typeof evaluation.score === 'number' &&
      typeof evaluation.ending === 'string' &&
      isGameStateLike(evaluation.state) &&
      typeof evaluation.state_token === 'string'
    ) {
      save.evaluation = evaluation;
    }
  }

  return save;
}

/** Read a previously saved signed game, or null when absent/corrupt. */
export function loadSavedGame(storage: Storage | null = defaultStorage()): SavedGame | null {
  if (!storage) {
    return null;
  }

  try {
    const raw = storage.getItem(SAVED_GAME_KEY);

    if (!raw) {
      return null;
    }

    const save = parseSave(raw);

    if (!save) {
      storage.removeItem(SAVED_GAME_KEY);
      return null;
    }

    return save;
  } catch {
    return null;
  }
}

/** Persist the signed state and token. Returns false when storage is blocked. */
export function saveGame(
  game: Omit<SavedGame, 'savedAt'>,
  storage: Storage | null = defaultStorage(),
): boolean {
  if (!storage) {
    return false;
  }

  const payload: StoredSave = {
    version: SAVE_VERSION,
    state: game.state,
    stateToken: game.stateToken,
    savedAt: Date.now(),
  };

  if (game.evaluation) {
    payload.evaluation = game.evaluation;
  }

  try {
    storage.setItem(SAVED_GAME_KEY, JSON.stringify(payload));
    return true;
  } catch {
    return false;
  }
}

export function clearSavedGame(
  storage: Storage | null = defaultStorage(),
): void {
  if (!storage) {
    return;
  }

  try {
    storage.removeItem(SAVED_GAME_KEY);
  } catch {
    // A blocked storage area should not stop the player from restarting.
  }
}
