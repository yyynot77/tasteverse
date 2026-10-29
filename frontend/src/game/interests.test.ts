import { describe, expect, it } from 'vitest';

import { parseInterests } from './interests';

describe('parseInterests', () => {
  it('trims, splits, and removes duplicates', () => {
    const result = parseInterests({
      movies: ' Inception, Spirited Away, inception ',
      music: 'jazz\ncity pop',
      food: 'ramen,  ramen',
    });

    expect(result).toEqual({
      ok: true,
      playerInterests: {
        movies: ['Inception', 'Spirited Away'],
        music: ['jazz', 'city pop'],
        food: ['ramen'],
      },
    });
  });

  it('requires at least one non-empty interest', () => {
    const result = parseInterests({ movies: ' ', music: '', food: '' });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/at least one/i);
    }
  });

  it('enforces the per-category item cap', () => {
    const result = parseInterests({
      movies: 'a,b,c,d,e,f',
      music: '',
      food: '',
    });

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toMatch(/5 entries/i);
    }
  });
});
