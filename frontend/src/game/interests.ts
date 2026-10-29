import type { PlayerInterests } from '../api/types';

export interface InterestDraft {
  movies: string;
  music: string;
  food: string;
}

const MAX_ITEMS = 5;
const MAX_LENGTH = 80;
const SEPARATORS = /[,，;\n]+/;

export type ParsedInterests =
  | { ok: true; playerInterests: PlayerInterests }
  | { ok: false; error: string };

function parseList(raw: string, label: string): string[] | string {
  const seen = new Set<string>();
  const items: string[] = [];

  for (const part of raw.split(SEPARATORS)) {
    const item = part.trim();

    if (!item) {
      continue;
    }

    if (item.length > MAX_LENGTH) {
      return `${label} entries must be ${MAX_LENGTH} characters or fewer.`;
    }

    const key = item.toLocaleLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      items.push(item);
    }
  }

  if (items.length > MAX_ITEMS) {
    return `Keep ${label.toLowerCase()} to ${MAX_ITEMS} entries or fewer.`;
  }

  return items;
}

/**
 * Parse the three comma/newline-separated interest fields into the exact shape
 * accepted by `POST /api/game/start`.
 */
export function parseInterests(draft: InterestDraft): ParsedInterests {
  const movies = parseList(draft.movies, 'Movie');
  const music = parseList(draft.music, 'Music');
  const food = parseList(draft.food, 'Food');

  for (const result of [movies, music, food]) {
    if (typeof result === 'string') {
      return { ok: false, error: result };
    }
  }

  const playerInterests: PlayerInterests = {
    movies: movies as string[],
    music: music as string[],
    food: food as string[],
  };

  if (
    playerInterests.movies.length === 0 &&
    playerInterests.music.length === 0 &&
    playerInterests.food.length === 0
  ) {
    return {
      ok: false,
      error: 'Add at least one movie, musician, or food to open your field journal.',
    };
  }

  return { ok: true, playerInterests };
}
