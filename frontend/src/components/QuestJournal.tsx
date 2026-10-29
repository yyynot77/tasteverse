import type { GameState } from '../api/types';
import { NPC_BY_ID } from '../game/npcs';
import type { NpcId } from '../game/types';

interface QuestJournalProps {
  state: GameState;
}

const STAGE_LABELS = {
  explore: 'Explore the square',
  plan: 'Plan the night',
  complete: 'The ending is written',
} as const;

const STEPS = ['Explore', 'Plan', 'Ending'] as const;

const NPC_ORDER: NpcId[] = ['mara', 'jun', 'theo'];

function QuestJournal({ state }: QuestJournalProps) {
  const metCount = state.interacted_npcs.length;

  return (
    <section className="paper-panel p-4 sm:p-5" aria-labelledby="quest-heading">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-tomato">
            Field journal · progress
          </p>
          <h2
            id="quest-heading"
            className="mt-1 font-display text-2xl font-bold leading-tight"
          >
            {STAGE_LABELS[state.stage]}
          </h2>
        </div>
        <span className="stamp shrink-0">
          {metCount}/3 met
        </span>
      </div>

      <ol className="mt-4 grid grid-cols-3 gap-1" aria-label="Quest stages">
        {STEPS.map((step, index) => {
          const done =
            (state.stage === 'explore' && index === 0) ||
            (state.stage === 'plan' && index <= 1) ||
            state.stage === 'complete';
          const current =
            (state.stage === 'explore' && index === 0) ||
            (state.stage === 'plan' && index === 1) ||
            (state.stage === 'complete' && index === 2);

          return (
            <li
              key={step}
              aria-current={current ? 'step' : undefined}
              className={`border-t-2 pt-1.5 ${
                done ? 'border-tomato' : 'border-ink/20'
              }`}
            >
              <span className="block font-mono text-[9px] font-bold uppercase tracking-wider text-ink/45">
                0{index + 1}
              </span>
              <span
                className={`mt-0.5 block text-[11px] font-bold ${
                  done ? 'text-ink' : 'text-ink/45'
                }`}
              >
                {step}
              </span>
            </li>
          );
        })}
      </ol>

      <ul className="mt-4 space-y-2">
        {NPC_ORDER.map((npcId) => {
          const npc = NPC_BY_ID[npcId];
          const met = state.interacted_npcs.includes(npcId);
          const relationship = state.relationships[npcId];

          return (
            <li
              key={npcId}
              className={`flex items-center gap-3 border-2 px-2.5 py-2 ${
                met
                  ? 'border-moss/70 bg-moss/10'
                  : 'border-ink/15 bg-paper-light/45'
              }`}
            >
              <span
                aria-hidden="true"
                className={`grid h-7 w-7 shrink-0 place-items-center border-2 font-mono text-[11px] font-bold ${
                  met
                    ? 'border-moss bg-moss text-paper-light'
                    : 'border-ink/25 text-ink/40'
                }`}
              >
                {met ? '✓' : npc.name.slice(0, 1)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-baseline justify-between gap-2">
                  <span className="font-display text-base font-bold leading-none">
                    {npc.name}
                  </span>
                  <span className="font-mono text-[9px] font-bold uppercase tracking-wide text-ink/45">
                    {met ? `rapport ${relationship}` : 'not met'}
                  </span>
                </span>
                <span className="mt-1 block truncate text-[11px] text-ink/55">
                  {npc.role}
                </span>
              </span>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 border-t-2 border-ink/15 pt-3">
        <h3 className="font-mono text-[9px] font-bold uppercase tracking-[0.18em] text-ink/55">
          Your starting taste
        </h3>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {(
            [
              ['Movies', state.player_interests.movies],
              ['Music', state.player_interests.music],
              ['Food', state.player_interests.food],
            ] as const
          ).flatMap(([label, values]) =>
            values.length === 0
              ? []
              : values.map((value) => (
                  <span
                    key={`${label}-${value}`}
                    className="border border-ink/25 bg-paper-light px-1.5 py-0.5 text-[10px] font-semibold"
                  >
                    <span className="font-mono text-[8px] uppercase tracking-wide text-tomato">
                      {label}
                    </span>{' '}
                    {value}
                  </span>
                )),
          )}
        </div>
        {state.clues.length > 0 ? (
          <p className="mt-3 font-mono text-[10px] font-bold uppercase tracking-wide text-moss">
            {state.clues.length} clue{state.clues.length === 1 ? '' : 's'} in the
            journal
          </p>
        ) : null}
      </div>
    </section>
  );
}

export default QuestJournal;
