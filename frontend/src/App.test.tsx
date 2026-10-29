import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import type {
  DialogueResponse,
  Ending,
  EvidenceStatus,
  GameState,
  PlanEvaluateResponse,
} from './api/types';
import type { TownEventBridge } from './game/events';
import { NPC_BY_ID } from './game/npcs';
import { TownScene } from './game/scenes/TownScene';
import { SAVED_GAME_KEY, saveGame } from './game/storage';
import type { NpcId } from './game/types';

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

const NPC_IDS: NpcId[] = ['mara', 'jun', 'theo'];

const BASE_STATE: GameState = {
  player_interests: {
    movies: ['Inception'],
    music: ['jazz'],
    food: ['ramen'],
  },
  session_id: '11111111-1111-4111-8111-111111111111',
  state_version: 0,
  stage: 'explore',
  relationships: { mara: 0, jun: 0, theo: 0 },
  clues: [],
  interacted_npcs: [],
  applied_event_ids: [],
  plan: null,
  cultural_matches: null,
  score: null,
  ending: null,
};

const fetchMock = vi.fn();

function makeState(overrides: Partial<GameState> = {}): GameState {
  return {
    ...BASE_STATE,
    ...overrides,
    player_interests: overrides.player_interests ?? BASE_STATE.player_interests,
    relationships: overrides.relationships ?? BASE_STATE.relationships,
    clues: overrides.clues ?? [],
    interacted_npcs: overrides.interacted_npcs ?? [],
    applied_event_ids: overrides.applied_event_ids ?? [],
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  } as Response;
}

function errorResponse(
  status: number,
  code: string,
  message: string,
  retryable: boolean,
): Response {
  return jsonResponse({ error: { code, message, retryable } }, status);
}

function currentBridge(): TownEventBridge {
  const config = phaserMock.game.mock.calls.at(-1)?.[0] as {
    scene: TownScene[];
  };

  return config.scene[0].bridge;
}

function requestBody(index: number): Record<string, unknown> {
  const call = fetchMock.mock.calls[index] as [string, RequestInit];
  return JSON.parse(String(call[1].body)) as Record<string, unknown>;
}

function requestUrl(index: number): string {
  return String(fetchMock.mock.calls[index]?.[0]);
}

function makeDialogueResponse(
  npcId: NpcId,
  state: GameState,
  previousState: GameState,
  message: string,
): DialogueResponse {
  const npc = NPC_BY_ID[npcId];

  return {
    reply: `${npc.name} says the square is listening.`,
    evidence: [
      {
        source: 'qloo',
        entity_id: `qloo-${npcId}`,
        label: `${npc.name}'s verified pick`,
        query_type: 'urn:entity',
        signal: 0.82,
      },
    ],
    tool_trace: [],
    tool_calls_executed: 1,
    transition: {
      npc_id: npcId,
      applied: true,
      relationship_before: previousState.relationships[npcId],
      relationship_after: state.relationships[npcId],
      stage_before: previousState.stage,
      stage_after: state.stage,
      reasons: ['Interaction recorded.'],
    },
    state,
    state_token: `v1.dialogue.${npcId}`,
    conversation: [
      { role: 'user', content: message },
      { role: 'assistant', content: `${npc.name} says the square is listening.` },
    ],
  };
}

function makeEvaluation(
  ending: Ending,
  score: number,
  evidenceStatus: EvidenceStatus = 'available',
): PlanEvaluateResponse {
  const available = evidenceStatus !== 'unavailable';
  const state = makeState({
    stage: 'complete',
    state_version: 8,
    interacted_npcs: [...NPC_IDS],
    relationships: { mara: 24, jun: 24, theo: 24 },
    plan: {
      movie: 'Inception',
      music: 'jazz',
      food: 'ramen',
      free_text: '',
    },
    score,
    ending,
    cultural_matches: available
      ? { movies: 0.8, music: 0.7, food: 0.6 }
      : null,
  });

  return {
    analysis: 'Backend analysis text.',
    evidence: available
      ? [
          {
            source: 'qloo',
            entity_id: 'qloo-mara',
            tag_id: null,
            label: 'Qloo movie anchor',
            query_type: 'urn:entity',
            component: 'movie',
            npc_id: 'mara',
            signal: 0.8,
          },
        ]
      : [],
    evidence_status: evidenceStatus,
    interpretation_status: 'not_needed',
    components: (['movie', 'music', 'food'] as const).map((component) => ({
      component,
      plan_value: component === 'movie' ? 'Inception' : component,
      evidence_count: available ? 1 : 0,
      evidence_available: available,
      score: available ? 78 : 0,
      npc_ids: available ? (['mara'] as NpcId[]) : [],
      reasons: [`${component} reason`],
    })),
    npcs: NPC_IDS.map((npcId) => ({
      npc_id: npcId,
      relationship: 24,
      clue_count: 0,
      evidence_count: available ? 1 : 0,
      score: available ? 30 : 24,
      reasons: [`${npcId} rules note`],
    })),
    reactions: NPC_IDS.map((npcId) => ({
      npc_id: npcId,
      name: NPC_BY_ID[npcId].name,
      relationship: 24,
      npc_score: 30,
      reaction:
        npcId === 'mara'
          ? 'Mara reacts warmly.'
          : `${NPC_BY_ID[npcId].name} reacts to the plan.`,
    })),
    reasons: ['Only verified provenance is counted.'],
    score,
    ending,
    state,
    state_token: `v1.plan.${ending}`,
  };
}

async function startFreshGame(state: GameState = makeState()) {
  fetchMock.mockResolvedValueOnce(
    jsonResponse({ state, state_token: 'v1.start' }),
  );
  render(<App />);

  fireEvent.change(screen.getByLabelText(/^Movies/), {
    target: { value: 'Inception' },
  });
  fireEvent.click(screen.getByRole('button', { name: /Enter the town/i }));

  await screen.findByRole('heading', {
    name: /Market Square, after sundown/i,
  });
  await waitFor(() => expect(phaserMock.game).toHaveBeenCalled());
  return currentBridge();
}

function resumeGame(
  state: GameState,
  stateToken = 'v1.saved',
  evaluation?: PlanEvaluateResponse,
) {
  saveGame({ state, stateToken, evaluation });
  render(<App />);
}

function openDialogue(npcId: NpcId) {
  const bridge = currentBridge();
  const panelClosed = vi.fn();
  bridge.on('npc:panel-closed', panelClosed);

  act(() => {
    bridge.emit('npc:interact', {
      npcId,
      npcName: NPC_BY_ID[npcId].name,
    });
  });

  return { panelClosed };
}

function sendDialogueMessage(npcId: NpcId, message: string) {
  const dialog = screen.getByRole('dialog');
  const input = within(dialog).getByLabelText(
    new RegExp(`Say something to ${NPC_BY_ID[npcId].name}`, 'i'),
  );

  fireEvent.change(input, { target: { value: message } });
  fireEvent.click(within(dialog).getByRole('button', { name: /^Send$/i }));

  return dialog;
}

describe('App start flow', () => {
  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    phaserMock.game.mockClear();
    phaserMock.destroy.mockClear();
  });

  it('requires at least one interest and starts a signed game', async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse({ state: makeState(), state_token: 'v1.start' }),
    );
    render(<App />);

    expect(fetchMock).not.toHaveBeenCalled();
    expect(phaserMock.game).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('button', { name: /Enter the town/i }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      /Add at least one movie, musician, or food/i,
    );
    expect(fetchMock).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText(/^Movies/), {
      target: { value: 'Inception, Spirited Away' },
    });
    fireEvent.change(screen.getByLabelText(/^Music/), {
      target: { value: 'jazz' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Enter the town/i }));

    expect(
      await screen.findByRole('heading', {
        name: /Market Square, after sundown/i,
      }),
    ).toBeInTheDocument();

    expect(requestUrl(0)).toMatch(/\/api\/game\/start$/);
    expect(requestBody(0)).toEqual({
      player_interests: {
        movies: ['Inception', 'Spirited Away'],
        music: ['jazz'],
        food: [],
      },
    });
    expect(phaserMock.game).toHaveBeenCalledTimes(1);

    const saved = JSON.parse(
      localStorage.getItem(SAVED_GAME_KEY) ?? '{}',
    ) as {
      state: GameState;
      stateToken: string;
    };
    expect(saved.stateToken).toBe('v1.start');
    expect(saved.state.interacted_npcs).toEqual([]);
  });

  it('offers a retry when the start request cannot reach the API', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    render(<App />);

    fireEvent.change(screen.getByLabelText(/^Food/), {
      target: { value: 'ramen' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Enter the town/i }));

    expect(await screen.findByText('Cannot reach the town')).toBeInTheDocument();

    fetchMock.mockResolvedValueOnce(
      jsonResponse({ state: makeState(), state_token: 'v1.retry' }),
    );
    fireEvent.click(screen.getByRole('button', { name: /Retry start/i }));

    expect(
      await screen.findByRole('heading', {
        name: /Market Square, after sundown/i,
      }),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('resumes a saved signed state without starting a new session', () => {
    const savedState = makeState({
      state_version: 3,
      interacted_npcs: ['mara'],
      relationships: { mara: 8, jun: 0, theo: 0 },
    });
    resumeGame(savedState, 'v1.saved-token');

    expect(fetchMock).not.toHaveBeenCalled();
    expect(
      screen.getByText('Saved game resumed from this browser.'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'Explore the square' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Signed state v3/i)).toBeInTheDocument();
    expect(screen.getAllByText('Mara').length).toBeGreaterThan(0);
  });

  it('clears saved progress through the restart confirmation', () => {
    resumeGame(makeState(), 'v1.saved-token');

    fireEvent.click(screen.getByRole('button', { name: /Start over/i }));
    fireEvent.click(screen.getByRole('button', { name: /Yes, start over/i }));

    expect(localStorage.getItem(SAVED_GAME_KEY)).toBeNull();
    expect(
      screen.getByRole('button', { name: /Enter the town/i }),
    ).toBeInTheDocument();
  });
});

describe('NPC dialogue', () => {
  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    phaserMock.game.mockClear();
    phaserMock.destroy.mockClear();
  });

  it.each(NPC_IDS)('routes %s conversation and shows Qloo evidence', async (npcId) => {
    const bridge = await startFreshGame();
    const panelClosed = vi.fn();
    bridge.on('npc:panel-closed', panelClosed);

    act(() => {
      bridge.emit('npc:interact', {
        npcId,
        npcName: NPC_BY_ID[npcId].name,
      });
    });

    const message = `What should the festival show, ${NPC_BY_ID[npcId].name}?`;
    const nextState = makeState({
      state_version: 1,
      interacted_npcs: [npcId],
      relationships: {
        mara: npcId === 'mara' ? 8 : 0,
        jun: npcId === 'jun' ? 8 : 0,
        theo: npcId === 'theo' ? 8 : 0,
      },
    });

    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        makeDialogueResponse(npcId, nextState, makeState(), message),
      ),
    );

    const dialog = sendDialogueMessage(npcId, message);

    expect(
      await within(dialog).findByText(
        new RegExp(`${NPC_BY_ID[npcId].name} says the square is listening`),
      ),
    ).toBeInTheDocument();
    expect(requestUrl(1)).toMatch(
      new RegExp(`/api/npc/${npcId}/dialogue$`),
    );
    expect(requestBody(1)).toMatchObject({
      state_token: 'v1.start',
      message,
      conversation: [],
      state: { stage: 'explore' },
    });
    expect(
      within(dialog).getByText(/Real Qloo evidence · 1/),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(new RegExp(`qloo-${npcId}`)),
    ).toBeInTheDocument();

    const saved = JSON.parse(
      localStorage.getItem(SAVED_GAME_KEY) ?? '{}',
    ) as { stateToken: string };
    expect(saved.stateToken).toBe(`v1.dialogue.${npcId}`);

    fireEvent.click(within(dialog).getByRole('button', { name: /^Close$/i }));

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(panelClosed).toHaveBeenCalledWith({ npcId });
  });

  it('unlocks the plan after the third resident is met', async () => {
    resumeGame(
      makeState({
        state_version: 2,
        interacted_npcs: ['mara', 'jun'],
        relationships: { mara: 8, jun: 8, theo: 0 },
      }),
      'v1.two-met',
    );

    const { panelClosed } = openDialogue('theo');
    const message = 'Tell me what the fountain remembers.';
    const unlockedState = makeState({
      state_version: 3,
      stage: 'plan',
      interacted_npcs: [...NPC_IDS],
      relationships: { mara: 8, jun: 8, theo: 8 },
    });

    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        makeDialogueResponse(
          'theo',
          unlockedState,
          makeState({
            interacted_npcs: ['mara', 'jun'],
            relationships: { mara: 8, jun: 8, theo: 0 },
          }),
          message,
        ),
      ),
    );

    const dialog = sendDialogueMessage('theo', message);

    expect(
      await screen.findByRole('heading', { name: 'Plan the night' }),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/3\/3 residents/),
    ).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /^Close$/i }));
    expect(panelClosed).toHaveBeenCalledWith({ npcId: 'theo' });

    expect(screen.getByLabelText(/^Movie/)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Send the plan/i }),
    ).toBeInTheDocument();
  });

  it('recovers from a network failure and still allows closing the panel', async () => {
    await startFreshGame();
    const { panelClosed } = openDialogue('mara');

    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const dialog = sendDialogueMessage('mara', 'Hello Mara');

    expect(
      await within(dialog).findByText('Cannot reach the town'),
    ).toBeInTheDocument();
    expect(
      within(dialog).getByRole('button', { name: /^Close$/i }),
    ).toBeEnabled();

    const nextState = makeState({
      state_version: 1,
      interacted_npcs: ['mara'],
      relationships: { mara: 8, jun: 0, theo: 0 },
    });
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        makeDialogueResponse('mara', nextState, makeState(), 'Hello Mara'),
      ),
    );
    fireEvent.click(within(dialog).getByRole('button', { name: /Try again/i }));

    expect(
      await within(dialog).findByText(/Real Qloo evidence · 1/),
    ).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /^Close$/i }));
    expect(panelClosed).toHaveBeenCalledWith({ npcId: 'mara' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('requires a restart when the signed state is rejected', async () => {
    await startFreshGame();
    openDialogue('jun');

    fetchMock.mockResolvedValueOnce(
      errorResponse(
        409,
        'state_integrity_error',
        'The signed game state is invalid.',
        false,
      ),
    );
    const dialog = sendDialogueMessage('jun', 'Is this record still signed?');

    expect(
      await within(dialog).findByText('This saved game is out of date'),
    ).toBeInTheDocument();

    fireEvent.click(
      within(dialog).getByRole('button', { name: /Start a new game/i }),
    );

    expect(localStorage.getItem(SAVED_GAME_KEY)).toBeNull();
    expect(
      screen.getByRole('button', { name: /Enter the town/i }),
    ).toBeInTheDocument();
  });
});

describe('plan evaluation and endings', () => {
  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
    phaserMock.game.mockClear();
    phaserMock.destroy.mockClear();
  });

  const ENDING_CASES: Array<{
    ending: Ending;
    title: string;
    score: number;
  }> = [
    { ending: 'perfect_harmony', title: 'Perfect Harmony', score: 91 },
    { ending: 'mixed_night', title: 'Mixed Night', score: 58 },
    { ending: 'cultural_chaos', title: 'Cultural Chaos', score: 22 },
  ];

  it.each(ENDING_CASES)(
    'submits the plan and renders the backend $title ending',
    async ({ ending, title, score }) => {
      resumeGame(
        makeState({
          stage: 'plan',
          state_version: 4,
          interacted_npcs: [...NPC_IDS],
          relationships: { mara: 24, jun: 24, theo: 24 },
        }),
        'v1.plan-state',
      );

      fireEvent.change(screen.getByLabelText(/^Movie/), {
        target: { value: 'Inception' },
      });
      fireEvent.change(screen.getByLabelText(/^Music/), {
        target: { value: 'jazz' },
      });
      fireEvent.change(screen.getByLabelText(/^Food/), {
        target: { value: 'ramen' },
      });

      const evaluation = makeEvaluation(ending, score);
      fetchMock.mockResolvedValueOnce(jsonResponse(evaluation));

      fireEvent.click(screen.getByRole('button', { name: /Send the plan/i }));

      expect(
        await screen.findByRole('heading', { name: title }),
      ).toBeInTheDocument();
      expect(requestUrl(0)).toMatch(/\/api\/plan\/evaluate$/);
      expect(requestBody(0)).toMatchObject({
        state_token: 'v1.plan-state',
        plan: {
          movie: 'Inception',
          music: 'jazz',
          food: 'ramen',
          free_text: '',
        },
      });
      expect(screen.getByTestId('ending-score')).toHaveTextContent(
        `${score}/100`,
      );
      expect(screen.getByText('Evidence available')).toBeInTheDocument();
      expect(screen.getByText('Backend analysis text.')).toBeInTheDocument();
      expect(screen.getByText('movie reason')).toBeInTheDocument();
      expect(screen.getByText('Mara reacts warmly.')).toBeInTheDocument();

      const saved = JSON.parse(
        localStorage.getItem(SAVED_GAME_KEY) ?? '{}',
      ) as { stateToken: string; evaluation?: { ending: Ending } };
      expect(saved.stateToken).toBe(`v1.plan.${ending}`);
      expect(saved.evaluation?.ending).toBe(ending);
    },
  );

  it('retries a 503 plan evaluation without re-entering the plan', async () => {
    resumeGame(
      makeState({
        stage: 'plan',
        interacted_npcs: [...NPC_IDS],
        relationships: { mara: 8, jun: 8, theo: 8 },
      }),
      'v1.plan-retry',
    );

    fireEvent.change(screen.getByLabelText(/^Movie/), {
      target: { value: 'Inception' },
    });

    fetchMock.mockResolvedValueOnce(
      errorResponse(
        503,
        'plan_interpretation_unavailable',
        'The planner is unavailable.',
        true,
      ),
    );
    fireEvent.click(screen.getByRole('button', { name: /Send the plan/i }));

    expect(
      await screen.findByText('The judges need a moment'),
    ).toBeInTheDocument();

    fetchMock.mockResolvedValueOnce(
      jsonResponse(makeEvaluation('mixed_night', 58)),
    );
    fireEvent.click(screen.getByRole('button', { name: /Retry plan/i }));

    expect(
      await screen.findByRole('heading', { name: /Mixed Night/i }),
    ).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(requestBody(1)).toMatchObject({
      plan: { movie: 'Inception', music: '', food: '', free_text: '' },
    });
  });

  it('renders an empty-evidence ending conservatively without invented evidence', async () => {
    resumeGame(
      makeState({
        stage: 'plan',
        interacted_npcs: [...NPC_IDS],
        relationships: { mara: 8, jun: 8, theo: 8 },
      }),
      'v1.empty-evidence',
    );

    fireEvent.change(screen.getByLabelText(/Field note/i), {
      target: { value: 'A night of surprises and no fixed bill.' },
    });
    fetchMock.mockResolvedValueOnce(
      jsonResponse(makeEvaluation('cultural_chaos', 0, 'unavailable')),
    );
    fireEvent.click(screen.getByRole('button', { name: /Send the plan/i }));

    expect(
      await screen.findByRole('heading', { name: /Cultural Chaos/i }),
    ).toBeInTheDocument();
    expect(screen.getByText('Evidence unavailable')).toBeInTheDocument();
    expect(screen.getByText(/The ledger is empty/i)).toBeInTheDocument();
    expect(screen.getByTestId('ending-score')).toHaveTextContent('0/100');
  });
});
