import { describe, expect, it, vi } from 'vitest';

import { TownEventBridge } from './events';

describe('TownEventBridge', () => {
  it('routes NPC interaction payloads to interaction subscribers only', () => {
    const bridge = new TownEventBridge();
    const interactionListener = vi.fn();
    const closeListener = vi.fn();

    bridge.on('npc:interact', interactionListener);
    bridge.on('npc:panel-closed', closeListener);

    bridge.emit('npc:interact', { npcId: 'mara', npcName: 'Mara' });

    expect(interactionListener).toHaveBeenCalledOnce();
    expect(interactionListener).toHaveBeenCalledWith({
      npcId: 'mara',
      npcName: 'Mara',
    });
    expect(closeListener).not.toHaveBeenCalled();
  });

  it('unsubscribes cleanly and supports multiple listeners', () => {
    const bridge = new TownEventBridge();
    const first = vi.fn();
    const second = vi.fn();
    const stopFirst = bridge.on('npc:panel-closed', first);

    bridge.on('npc:panel-closed', second);
    stopFirst();
    stopFirst();
    bridge.emit('npc:panel-closed', { npcId: 'jun' });

    expect(first).not.toHaveBeenCalled();
    expect(second).toHaveBeenCalledWith({ npcId: 'jun' });
  });

  it('routes proximity null and clears all subscriptions on teardown', () => {
    const bridge = new TownEventBridge();
    const proximity = vi.fn();

    bridge.on('npc:proximity', proximity);
    bridge.emit('npc:proximity', { npcId: 'theo' });
    bridge.emit('npc:proximity', { npcId: null });

    expect(proximity).toHaveBeenNthCalledWith(1, { npcId: 'theo' });
    expect(proximity).toHaveBeenNthCalledWith(2, { npcId: null });

    bridge.clear();
    bridge.emit('npc:proximity', { npcId: 'mara' });

    expect(proximity).toHaveBeenCalledTimes(2);
  });

  it('uses a stable snapshot when a listener unsubscribes during emit', () => {
    const bridge = new TownEventBridge();
    const second = vi.fn();
    const stopFirst = bridge.on('npc:interact', () => {
      stopFirst();
    });

    bridge.on('npc:interact', second);
    bridge.emit('npc:interact', { npcId: 'theo', npcName: 'Theo' });

    expect(second).toHaveBeenCalledOnce();
  });
});
