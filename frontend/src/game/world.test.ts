import { describe, expect, it } from 'vitest';

import { NPCS } from './npcs';
import {
  findNearestNpcInRange,
  INTERACTION_RADIUS,
  isPositionBlocked,
  movePlayer,
  PLAYER_HALF_HEIGHT,
  PLAYER_HALF_WIDTH,
  PLAYER_SPEED,
  TOWN_BOUNDS,
  TOWN_OBSTACLES,
  type Obstacle,
} from './world';

const WIDE_BOUNDS = {
  left: 0,
  top: 0,
  right: 960,
  bottom: 540,
} as const;

const testObstacle: Obstacle = {
  id: 'test-wall',
  kind: 'building',
  x: 100,
  y: 100,
  width: 40,
  height: 40,
};

describe('movePlayer', () => {
  it('normalizes diagonal movement to the same speed as cardinal movement', () => {
    const start = { x: 480, y: 300 };
    const diagonal = movePlayer(start, { x: 1, y: 1 }, 0.1, [], WIDE_BOUNDS);
    const horizontal = movePlayer(start, { x: 1, y: 0 }, 0.1, [], WIDE_BOUNDS);

    const diagonalDistance = Math.hypot(
      diagonal.x - start.x,
      diagonal.y - start.y,
    );
    const horizontalDistance = Math.hypot(
      horizontal.x - start.x,
      horizontal.y - start.y,
    );

    expect(diagonalDistance).toBeCloseTo(PLAYER_SPEED * 0.1, 5);
    expect(horizontalDistance).toBeCloseTo(PLAYER_SPEED * 0.1, 5);
    expect(diagonal.x - start.x).toBeCloseTo(diagonal.y - start.y, 5);
  });

  it('keeps the player inside the world boundary', () => {
    const leftEdge = movePlayer(
      {
        x: TOWN_BOUNDS.left + PLAYER_HALF_WIDTH,
        y: 300,
      },
      { x: -1, y: 0 },
      1,
      [],
      TOWN_BOUNDS,
    );
    const topEdge = movePlayer(
      {
        x: 480,
        y: TOWN_BOUNDS.top + PLAYER_HALF_HEIGHT,
      },
      { x: 0, y: -1 },
      1,
      [],
      TOWN_BOUNDS,
    );

    expect(leftEdge.x).toBe(TOWN_BOUNDS.left + PLAYER_HALF_WIDTH);
    expect(topEdge.y).toBe(TOWN_BOUNDS.top + PLAYER_HALF_HEIGHT);
  });

  it('stops at an obstacle instead of tunnelling through it', () => {
    const start = { x: 70, y: 120 };
    const result = movePlayer(start, { x: 1, y: 0 }, 1, [testObstacle], WIDE_BOUNDS);

    expect(result.x).toBeGreaterThan(start.x);
    expect(result.x).toBeLessThanOrEqual(testObstacle.x - PLAYER_HALF_WIDTH);
    expect(
      isPositionBlocked(result, [testObstacle], WIDE_BOUNDS),
    ).toBe(false);
  });

  it('slides along an obstacle when movement is diagonal', () => {
    const start = { x: 80, y: 120 };
    const result = movePlayer(
      start,
      { x: 1, y: 1 },
      0.1,
      [testObstacle],
      WIDE_BOUNDS,
    );

    expect(result.y).toBeGreaterThan(start.y);
    expect(result.x).toBeLessThanOrEqual(testObstacle.x - PLAYER_HALF_WIDTH);
    expect(
      isPositionBlocked(result, [testObstacle], WIDE_BOUNDS),
    ).toBe(false);
  });

  it('returns the starting position for zero input or a zero delta', () => {
    const start = { x: 480, y: 300 };

    expect(movePlayer(start, { x: 0, y: 0 }, 0.1, [], WIDE_BOUNDS)).toEqual(
      start,
    );
    expect(movePlayer(start, { x: 1, y: 1 }, 0, [], WIDE_BOUNDS)).toEqual(start);
  });
});

describe('isPositionBlocked', () => {
  it('detects boundaries, solids, and free ground', () => {
    expect(isPositionBlocked({ x: 2, y: 300 }, [], WIDE_BOUNDS)).toBe(true);
    expect(
      isPositionBlocked({ x: 110, y: 110 }, [testObstacle], WIDE_BOUNDS),
    ).toBe(true);
    expect(isPositionBlocked({ x: 300, y: 300 }, [testObstacle], WIDE_BOUNDS)).toBe(
      false,
    );
  });
});

describe('town content', () => {
  it('has exactly three uniquely named, uniquely positioned NPCs', () => {
    expect(NPCS).toHaveLength(3);
    expect(new Set(NPCS.map((npc) => npc.id)).size).toBe(3);
    expect(new Set(NPCS.map((npc) => npc.name)).size).toBe(3);
    expect(new Set(NPCS.map((npc) => `${npc.x},${npc.y}`)).size).toBe(3);
  });

  it('provides at least two solid town obstacles', () => {
    expect(TOWN_OBSTACLES.length).toBeGreaterThanOrEqual(2);
  });

  it('finds the nearest NPC only inside the interaction radius', () => {
    const mara = NPCS.find((npc) => npc.id === 'mara');
    const theo = NPCS.find((npc) => npc.id === 'theo');

    expect(mara).toBeDefined();
    expect(theo).toBeDefined();
    expect(findNearestNpcInRange({ x: mara!.x + 4, y: mara!.y + 4 })).toBe(mara);
    expect(findNearestNpcInRange({ x: theo!.x - 4, y: theo!.y + 4 })).toBe(theo);
    expect(
      findNearestNpcInRange({
        x: mara!.x + INTERACTION_RADIUS + 10,
        y: mara!.y,
      }),
    ).toBeNull();
    expect(findNearestNpcInRange({ x: 20, y: 500 })).toBeNull();
  });
});
