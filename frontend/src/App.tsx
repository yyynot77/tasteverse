import { useCallback, useEffect, useRef, useState } from 'react';

import type { GameState, PlanEvaluateResponse } from './api/types';
import DialoguePanel from './components/DialoguePanel';
import PlanPanel from './components/PlanPanel';
import QuestJournal from './components/QuestJournal';
import StartScreen from './components/StartScreen';
import { TownEventBridge } from './game/events';
import type { NpcDialogueLog, DialogueLogs } from './game/dialogueLog';
import { NPC_BY_ID } from './game/npcs';
import PhaserStage from './game/PhaserStage';
import {
  clearSavedGame,
  loadSavedGame,
  saveGame,
  type SavedGame,
} from './game/storage';
import type { NpcId, NpcInteraction } from './game/types';

const controls = [
  { keys: 'W A S D  /  Arrow keys', action: 'Move around town' },
  { keys: 'E  /  Enter', action: 'Talk to a nearby resident' },
  { keys: 'Escape', action: 'Close the conversation panel' },
];

const STAGE_BADGES = {
  explore: 'Explore',
  plan: 'Plan unlocked',
  complete: 'Ending written',
} as const;

function App() {
  const [initialSave] = useState<SavedGame | null>(() => loadSavedGame());
  const [session, setSession] = useState<SavedGame | null>(initialSave);
  const [notice, setNotice] = useState<string | null>(
    initialSave ? 'Saved game resumed from this browser.' : null,
  );
  const [storageWarning, setStorageWarning] = useState(false);
  const [bridge] = useState(() => new TownEventBridge());
  const [activeNpc, setActiveNpc] = useState<NpcInteraction | null>(null);
  const [nearbyNpcId, setNearbyNpcId] = useState<NpcId | null>(null);
  const [dialogueLogs, setDialogueLogs] = useState<DialogueLogs>({});
  const [restartConfirmOpen, setRestartConfirmOpen] = useState(false);
  const [mapMessage, setMapMessage] = useState<string | null>(null);
  const sessionRef = useRef<SavedGame | null>(initialSave);

  const commitSession = useCallback((next: SavedGame) => {
    sessionRef.current = next;
    setSession(next);
    setStorageWarning(!saveGame(next));
  }, []);

  const handleStarted = useCallback(
    (result: { state: GameState; state_token: string }) => {
      setDialogueLogs({});
      setActiveNpc(null);
      setNearbyNpcId(null);
      setNotice('New field journal opened. Meet all three residents.');
      commitSession({
        state: result.state,
        stateToken: result.state_token,
        savedAt: Date.now(),
      });
    },
    [commitSession],
  );

  const handleDialogueState = useCallback(
    (state: GameState, stateToken: string) => {
      const current = sessionRef.current;

      if (!current) {
        return;
      }

      const next: SavedGame = {
        ...current,
        state,
        stateToken,
        evaluation:
          state.stage === 'complete' ? current.evaluation : undefined,
        savedAt: Date.now(),
      };

      commitSession(next);
    },
    [commitSession],
  );

  const handlePlanEvaluated = useCallback(
    (result: PlanEvaluateResponse) => {
      commitSession({
        state: result.state,
        stateToken: result.state_token,
        evaluation: result,
        savedAt: Date.now(),
      });
      setActiveNpc(null);
      setNotice('The town has chosen an ending. Read it in your journal.');
    },
    [commitSession],
  );

  const restartGame = useCallback(() => {
    clearSavedGame();
    sessionRef.current = null;
    setSession(null);
    setActiveNpc(null);
    setNearbyNpcId(null);
    setDialogueLogs({});
    setRestartConfirmOpen(false);
    setNotice(null);
    setMapMessage(null);
    setStorageWarning(false);

    if (activeNpc) {
      bridge.emit('npc:panel-closed', { npcId: activeNpc.npcId });
    }
  }, [activeNpc, bridge]);

  useEffect(() => {
    const stopInteraction = bridge.on('npc:interact', (interaction) => {
      const current = sessionRef.current;

      if (!current || current.state.stage === 'complete') {
        setMapMessage(
          'The night is complete. Start a new game to talk with the residents again.',
        );
        return;
      }

      setMapMessage(null);
      setActiveNpc(interaction);
    });
    const stopProximity = bridge.on('npc:proximity', ({ npcId }) => {
      setNearbyNpcId(npcId);
    });

    return () => {
      stopInteraction();
      stopProximity();
    };
  }, [bridge]);

  const closeInteraction = useCallback(() => {
    if (!activeNpc) {
      return;
    }

    bridge.emit('npc:panel-closed', { npcId: activeNpc.npcId });
    setActiveNpc(null);
  }, [activeNpc, bridge]);

  useEffect(() => {
    if (!activeNpc) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closeInteraction();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeNpc, closeInteraction]);

  const handleLogChange = useCallback(
    (npcId: NpcId, log: NpcDialogueLog) => {
      setDialogueLogs((current) => ({ ...current, [npcId]: log }));
    },
    [],
  );

  if (!session) {
    return <StartScreen onStarted={handleStarted} />;
  }

  const { state, stateToken, evaluation } = session;
  const nearbyNpc = nearbyNpcId ? NPC_BY_ID[nearbyNpcId] : null;
  const complete = state.stage === 'complete';

  const mapStatus = mapMessage
    ? mapMessage
    : complete
      ? 'The ending is written. Start over to explore the square again.'
      : nearbyNpc
        ? `Near ${nearbyNpc.name} (${nearbyNpc.role}). Press E or Enter to talk.`
        : 'Walk the square to find Mara, Jun, and Theo.';

  return (
    <div className="festival-page min-h-screen text-ink">
      <a href="#town-map" className="skip-link">
        Skip to the town map
      </a>

      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-3 py-3 sm:px-6 sm:py-5">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink pb-3">
          <div className="flex items-center gap-3">
            <span className="brand-block" aria-hidden="true">
              TV
            </span>
            <div>
              <p className="font-mono text-[9px] font-bold uppercase tracking-[0.24em] text-tomato">
                TasteVerse · field journal
              </p>
              <p className="font-display text-xl font-bold leading-tight sm:text-2xl">
                Market Square Festival
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="stage-badge">{STAGE_BADGES[state.stage]}</span>
            {restartConfirmOpen ? (
              <div
                role="group"
                aria-label="Confirm restart"
                className="flex flex-wrap items-center gap-1 border-2 border-ink bg-paper-light px-2 py-1.5"
              >
                <span className="font-mono text-[9px] font-bold uppercase tracking-wide">
                  Clear saved progress?
                </span>
                <button
                  type="button"
                  onClick={restartGame}
                  className="border border-tomato bg-tomato px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-wide text-paper-light"
                >
                  Yes, start over
                </button>
                <button
                  type="button"
                  onClick={() => setRestartConfirmOpen(false)}
                  className="border border-ink/30 px-2 py-1 font-mono text-[9px] font-bold uppercase tracking-wide"
                >
                  Keep playing
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setRestartConfirmOpen(true)}
                className="border-2 border-ink bg-paper-light px-3 py-2 font-mono text-[10px] font-bold uppercase tracking-wider shadow-[2px_2px_0_#2b2620] transition hover:bg-mustard focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tomato"
              >
                Start over
              </button>
            )}
          </div>
        </header>

        {notice || storageWarning ? (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-l-4 border-moss bg-paper-light/70 px-3 py-2">
            <p role="status" className="text-xs leading-5 text-ink/70">
              {storageWarning
                ? 'This browser blocked local saves. Progress will last only for this tab.'
                : notice}
            </p>
            {notice ? (
              <button
                type="button"
                onClick={() => setNotice(null)}
                className="font-mono text-[9px] font-bold uppercase tracking-wider text-ink/50 underline underline-offset-2"
              >
                Dismiss
              </button>
            ) : null}
          </div>
        ) : null}

        <main className="mt-4 grid flex-1 items-start gap-4 lg:grid-cols-[minmax(0,1.55fr)_minmax(310px,0.8fr)] lg:gap-6">
          <section
            id="town-map"
            aria-labelledby="map-heading"
            className="min-w-0"
          >
            <div className="mb-2 flex flex-wrap items-end justify-between gap-2">
              <div>
                <p className="font-mono text-[9px] font-bold uppercase tracking-[0.2em] text-tomato">
                  The map · live
                </p>
                <h1
                  id="map-heading"
                  className="font-display text-2xl font-bold leading-tight sm:text-3xl"
                >
                  Market Square, after sundown
                </h1>
              </div>
              <p className="font-mono text-[9px] font-bold uppercase tracking-wider text-ink/45">
                960 × 540 · pixel town
              </p>
            </div>

            <div className="map-frame relative aspect-[16/9] max-h-[560px] w-full overflow-hidden">
              <PhaserStage bridge={bridge} />
              {activeNpc ? (
                <DialoguePanel
                  interaction={activeNpc}
                  gameState={state}
                  stateToken={stateToken}
                  log={dialogueLogs[activeNpc.npcId]}
                  onLogChange={handleLogChange}
                  onStateUpdate={handleDialogueState}
                  onClose={closeInteraction}
                  onRestart={restartGame}
                />
              ) : null}
            </div>

            <div
              role="status"
              aria-live="polite"
              className="mt-2 min-h-10 border-l-4 border-mustard bg-paper-light/60 px-3 py-2 text-xs leading-5 text-ink/70"
            >
              {mapStatus}
            </div>

            <div className="mt-3 grid gap-2 sm:grid-cols-[1.15fr_0.85fr]">
              <div className="border-2 border-ink/20 bg-paper-light/60 px-3 py-2.5">
                <h2 className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-tomato">
                  Town controls
                </h2>
                <ul className="mt-1.5 space-y-1 text-[11px] text-ink/70">
                  {controls.map((control) => (
                    <li key={control.keys} className="flex flex-wrap gap-x-2">
                      <kbd className="border border-ink/30 bg-paper px-1 py-0.5 font-mono text-[9px] font-bold text-ink">
                        {control.keys}
                      </kbd>
                      <span>{control.action}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="border-2 border-ink/20 bg-paper-light/60 px-3 py-2.5">
                <h2 className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-tomato">
                  How the night works
                </h2>
                <p className="mt-1.5 text-[11px] leading-5 text-ink/70">
                  Talk to all three residents to unlock the plan. Qloo evidence
                  appears separately from NPC prose; the backend owns every
                  score and ending.
                </p>
              </div>
            </div>
          </section>

          <aside className="min-w-0 space-y-4" aria-label="Field journal">
            <QuestJournal state={state} />

            <PlanPanel
              state={state}
              stateToken={stateToken}
              evaluation={evaluation}
              onEvaluated={handlePlanEvaluated}
              onRestart={restartGame}
            />

            <div className="border-t-2 border-ink/20 pt-2 text-[10px] leading-5 text-ink/50">
              <p>
                Signed state v{state.state_version} · session{' '}
                <span className="break-all font-mono">
                  {state.session_id.slice(0, 8)}
                </span>
                . Never edit the saved token by hand.
              </p>
            </div>
          </aside>
        </main>

        <footer className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t-2 border-ink/30 pt-3 font-mono text-[9px] uppercase tracking-[0.14em] text-ink/50">
          <p>TasteVerse · one town, three residents, one night</p>
          <p>Signed state · server-scored endings</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
