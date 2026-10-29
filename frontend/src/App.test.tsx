import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { TownScene } from './game/scenes/TownScene';

const phaserMock = vi.hoisted(() => ({
  game: vi.fn(),
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
      // No-op for the jsdom smoke test.
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

describe('App', () => {
  beforeEach(() => {
    phaserMock.game.mockClear();
  });

  it('renders the start screen and initializes the Phaser scene', () => {
    render(<App />);

    expect(
      screen.getByRole('heading', { name: /TasteVerse/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Enter the town/i }),
    ).toBeInTheDocument();
    expect(screen.getByTestId('phaser-stage')).toBeInTheDocument();
    expect(screen.getByTestId('scene-status')).toHaveTextContent(
      'Phaser scene initialized',
    );

    expect(phaserMock.game).toHaveBeenCalledTimes(1);
    const config = phaserMock.game.mock.calls[0]?.[0] as {
      scene: unknown[];
      width: number;
      height: number;
    };
    expect(config.scene).toContain(TownScene);
    expect(config.width).toBe(960);
    expect(config.height).toBe(540);
  });

  it('dismisses the start screen when the player enters the town', () => {
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /Enter the town/i }));

    expect(
      screen.queryByRole('button', { name: /Enter the town/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByText('Scaffold active')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Return to start/i }),
    ).toBeInTheDocument();
  });
});
