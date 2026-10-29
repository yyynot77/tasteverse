import type { NpcId, NpcInteraction } from './types';

/**
 * Typed React <-> Phaser event bridge.
 *
 * React subscribes to `npc:interact` to open the interaction panel and emits
 * `npc:panel-closed` to return control to the scene. Keeping the game behind
 * this boundary means later API-backed dialogue can replace the panel contents
 * without teaching the scene about HTTP or React.
 */
export interface TownEvents {
  'npc:interact': NpcInteraction;
  'npc:panel-closed': { npcId: NpcId };
  'npc:proximity': { npcId: NpcId | null };
}

export type TownEventName = keyof TownEvents;

type TownEventHandler<K extends TownEventName> = (
  payload: TownEvents[K],
) => void;

export class TownEventBridge {
  private readonly listeners = new Map<
    TownEventName,
    Set<(payload: never) => void>
  >();

  /** Subscribe to one typed event. Returns an idempotent unsubscribe function. */
  on<K extends TownEventName>(
    event: K,
    handler: TownEventHandler<K>,
  ): () => void {
    let handlers = this.listeners.get(event);

    if (!handlers) {
      handlers = new Set();
      this.listeners.set(event, handlers);
    }

    handlers.add(handler as (payload: never) => void);

    return () => {
      handlers?.delete(handler as (payload: never) => void);
    };
  }

  /** Emit one typed event to a stable snapshot of current subscribers. */
  emit<K extends TownEventName>(event: K, payload: TownEvents[K]): void {
    const handlers = this.listeners.get(event);

    if (!handlers) {
      return;
    }

    for (const handler of [...handlers]) {
      handler(payload as never);
    }
  }

  /** Remove every subscription, used when the owning React tree unmounts. */
  clear(): void {
    this.listeners.clear();
  }
}
