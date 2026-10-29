import { NPCS } from './npcs';
import type { NpcDefinition, Vector2 } from './types';

export const WORLD_WIDTH = 960;
export const WORLD_HEIGHT = 540;

export const PLAYER_HALF_WIDTH = 7;
export const PLAYER_HALF_HEIGHT = 10;
export const PLAYER_SPEED = 150;
export const INTERACTION_RADIUS = 64;

/** Largest collision sub-step, so fast frames cannot tunnel through a wall. */
const MAX_MOVE_STEP = 4;

/** Player centre is kept inside this rectangle (also the world boundary). */
export const TOWN_BOUNDS = {
  left: 16,
  top: 76,
  right: WORLD_WIDTH - 16,
  bottom: WORLD_HEIGHT - 16,
} as const;

export type ObstacleKind =
  | 'building'
  | 'fountain'
  | 'stall'
  | 'crates'
  | 'tree'
  | 'bench';

export interface Obstacle {
  readonly id: string;
  readonly kind: ObstacleKind;
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

/** Solid rectangles shared by rendering and collision. */
export const TOWN_OBSTACLES: readonly Obstacle[] = [
  { id: 'bakery', kind: 'building', x: 60, y: 96, width: 220, height: 118 },
  { id: 'town-hall', kind: 'building', x: 350, y: 80, width: 260, height: 118 },
  { id: 'record-shop', kind: 'building', x: 690, y: 96, width: 210, height: 118 },
  { id: 'fountain', kind: 'fountain', x: 442, y: 250, width: 76, height: 62 },
  { id: 'market-stall', kind: 'stall', x: 654, y: 372, width: 126, height: 58 },
  { id: 'crates', kind: 'crates', x: 242, y: 392, width: 48, height: 42 },
  { id: 'oak-left', kind: 'tree', x: 52, y: 446, width: 36, height: 44 },
  { id: 'oak-right', kind: 'tree', x: 872, y: 446, width: 36, height: 44 },
  { id: 'bench', kind: 'bench', x: 350, y: 456, width: 88, height: 22 },
];

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function overlapsObstacle(
  position: Vector2,
  obstacle: Obstacle,
  halfWidth = PLAYER_HALF_WIDTH,
  halfHeight = PLAYER_HALF_HEIGHT,
): boolean {
  const left = position.x - halfWidth;
  const right = position.x + halfWidth;
  const top = position.y - halfHeight;
  const bottom = position.y + halfHeight;

  return (
    right > obstacle.x &&
    left < obstacle.x + obstacle.width &&
    bottom > obstacle.y &&
    top < obstacle.y + obstacle.height
  );
}

/** True when the player centre is outside the world or inside a solid. */
export function isPositionBlocked(
  position: Vector2,
  obstacles: readonly Obstacle[] = TOWN_OBSTACLES,
  bounds: { left: number; top: number; right: number; bottom: number } = TOWN_BOUNDS,
): boolean {
  if (
    position.x - PLAYER_HALF_WIDTH < bounds.left ||
    position.x + PLAYER_HALF_WIDTH > bounds.right ||
    position.y - PLAYER_HALF_HEIGHT < bounds.top ||
    position.y + PLAYER_HALF_HEIGHT > bounds.bottom
  ) {
    return true;
  }

  return obstacles.some((obstacle) => overlapsObstacle(position, obstacle));
}

/**
 * Move a player for one frame with normalized diagonal speed and per-axis
 * sliding collision. Pure and deterministic so movement can be unit tested
 * without Phaser.
 */
export function movePlayer(
  position: Vector2,
  input: Vector2,
  deltaSeconds: number,
  obstacles: readonly Obstacle[] = TOWN_OBSTACLES,
  bounds: { left: number; top: number; right: number; bottom: number } = TOWN_BOUNDS,
): Vector2 {
  const length = Math.hypot(input.x, input.y);

  if (length === 0 || deltaSeconds <= 0) {
    return { x: position.x, y: position.y };
  }

  const distance = PLAYER_SPEED * deltaSeconds;
  const dx = (input.x / length) * distance;
  const dy = (input.y / length) * distance;
  const steps = Math.max(
    1,
    Math.ceil(Math.max(Math.abs(dx), Math.abs(dy)) / MAX_MOVE_STEP),
  );
  const stepX = dx / steps;
  const stepY = dy / steps;

  let x = clamp(
    position.x,
    bounds.left + PLAYER_HALF_WIDTH,
    bounds.right - PLAYER_HALF_WIDTH,
  );
  let y = clamp(
    position.y,
    bounds.top + PLAYER_HALF_HEIGHT,
    bounds.bottom - PLAYER_HALF_HEIGHT,
  );

  const blocked = (candidateX: number, candidateY: number): boolean =>
    obstacles.some((obstacle) =>
      overlapsObstacle({ x: candidateX, y: candidateY }, obstacle),
    );

  for (let step = 0; step < steps; step += 1) {
    const nextX = clamp(
      x + stepX,
      bounds.left + PLAYER_HALF_WIDTH,
      bounds.right - PLAYER_HALF_WIDTH,
    );

    if (!blocked(nextX, y)) {
      x = nextX;
    }

    const nextY = clamp(
      y + stepY,
      bounds.top + PLAYER_HALF_HEIGHT,
      bounds.bottom - PLAYER_HALF_HEIGHT,
    );

    if (!blocked(x, nextY)) {
      y = nextY;
    }
  }

  return { x, y };
}

/** Closest NPC within interaction range, or null when nobody is close. */
export function findNearestNpcInRange(
  position: Vector2,
  npcs: readonly NpcDefinition[] = NPCS,
  radius: number = INTERACTION_RADIUS,
): NpcDefinition | null {
  let nearest: NpcDefinition | null = null;
  let nearestDistance = radius;

  for (const npc of npcs) {
    const distance = Math.hypot(npc.x - position.x, npc.y - position.y);

    if (distance <= nearestDistance) {
      nearest = npc;
      nearestDistance = distance;
    }
  }

  return nearest;
}
