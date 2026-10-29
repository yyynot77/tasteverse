import { StrictMode } from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import type { TownEventBridge } from './game/events';
import { TownScene } from './game/scenes/TownScene';

const phaserMock = vi.hoisted(() => ({
  game: vi.fn(),
  destroy: vi.fn(),
}));

vi.mock('phaser', () => {
  class Scene {
    constructor(..._args: unknown[]) {
      void _args;
    }
  }

  class Game {
    constructor(config: unknown) {
      phaserMock.game(config);
    }

    destroy(): void {
      phaserMock.destroy();
    }
  }

  return {
    default: {
      AUTO: 'AUTO',
      Scale: {
        FIT: 'FIT',
        CENTER_BOTH: 'CENTER_BOTH',
      },
      Game,
      Scene,
    },
  };
});

function currentScene(): TownScene {
  const config = phaserMock.game.mock.calls[0]?.[0] as {
    scene: TownScene[];
  };

  return config.scene[0];
}

function currentBridge(): TownEventBridge {
  return currentScene().bridge;
}

describe('App', () => {
  beforeEach(() => {
    phaserMock.game.mockClear();
    phaserMock.destroy.mockClear();
  });

  it('renders the start screen and initializes the 960x540 town scene', () => {
    render(<App />);

    expect(
      screen.getByRole('heading', { name: /TasteVerse/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Enter the town/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId('phaser-stage')).toBeInTheDocument();
    expect(screen.getByTestId('scene-status')).toHaveTextContent(
      'Town scene ready',
    );
    expect(screen.getByText(/Task 03 · Playable town/i)).toBeInTheDocument();

    expect(phaserMock.game).toHaveBeenCalledTimes(1);
    const config = phaserMock.game.mock.calls[0]?.[0] as {
      scene: unknown[];
      width: number;
      height: number;
    };
    expect(config.scene[0]).toBeInstanceOf(TownScene);
    expect(config.width).toBe(960);
    expect(config.height).toBe(540);
  });

  it('dismisses the start screen when the player enters the town', () => {
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /Enter the town/i }));

    expect(
      screen.queryByRole('button', { name: /Enter the town/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText('Town scene active')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Return to start/i }),
    ).toBeInTheDocument();
  });

  it('opens an NPC panel from the typed bridge and closes it with the button', () => {
    render(<App />);
    const bridge = currentBridge();
    const panelClosed = vi.fn();
    bridge.on('npc:panel-closed', panelClosed);

    act(() => {
      bridge.emit('npc:interact', { npcId: 'mara', npcName: 'Mara' });
    });

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(
      within(dialog).getByRole('heading', { name: 'Mara' }),
    ).toBeInTheDocument();
    expect(within(dialog).getByText('Baker')).toBeInTheDocument();
    expect(
      within(dialog).getByRole('button', { name: /Close conversation/i }),
    ).toHaveFocus();

    fireEvent.click(
      within(dialog).getByRole('button', { name: /Close conversation/i }),
    );

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(panelClosed).toHaveBeenCalledWith({ npcId: 'mara' });
  });

  it('dismisses the panel with Escape and signals the scene to resume', () => {
    render(<App />);
    const bridge = currentBridge();
    const panelClosed = vi.fn();
    bridge.on('npc:panel-closed', panelClosed);

    act(() => {
      bridge.emit('npc:interact', { npcId: 'theo', npcName: 'Theo' });
    });
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(panelClosed).toHaveBeenCalledWith({ npcId: 'theo' });
  });

  it('shows accessible proximity copy from scene events', () => {
    render(<App />);
    const bridge = currentBridge();

    act(() => {
      bridge.emit('npc:proximity', { npcId: 'jun' });
    });

    expect(
      screen.getByText(/Near Jun \(Record shop owner\)/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('list', { name: /Town controls/i }),
    ).toBeInTheDocument();
  });

  it('destroys the Phaser game on unmount', () => {
    const { unmount } = render(<App />);

    unmount();

    expect(phaserMock.destroy).toHaveBeenCalledTimes(1);
  });

  it('does not leak the provisional Strict Mode game', () => {
    const { unmount } = render(
      <StrictMode>
        <App />
      </StrictMode>,
    );

    expect(phaserMock.game).toHaveBeenCalledTimes(2);
    expect(phaserMock.destroy).toHaveBeenCalledTimes(1);

    unmount();
    expect(phaserMock.destroy).toHaveBeenCalledTimes(2);
  });
});
