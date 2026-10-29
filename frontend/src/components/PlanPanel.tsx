import { useState, type FormEvent } from 'react';

import { evaluatePlan } from '../api/client';
import type {
  GameState,
  Plan,
  PlanEvaluateResponse,
} from '../api/types';
import { NPC_BY_ID } from '../game/npcs';
import EndingReport from './EndingReport';
import ErrorNotice from './ErrorNotice';

interface PlanPanelProps {
  state: GameState;
  stateToken: string;
  evaluation?: PlanEvaluateResponse;
  onEvaluated: (result: PlanEvaluateResponse) => void;
  onRestart: () => void;
}

const EMPTY_PLAN: Plan = { movie: '', music: '', food: '', free_text: '' };

function PlanLocked({ state }: { state: GameState }) {
  const met = state.interacted_npcs.length;

  return (
    <section className="paper-panel p-5" aria-labelledby="plan-locked-heading">
      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-tomato">
        Festival plan · locked
      </p>
      <h2
        id="plan-locked-heading"
        className="mt-1 font-display text-2xl font-bold leading-tight"
      >
        Meet the whole square first
      </h2>
      <p className="mt-2 text-sm leading-6 text-ink/75">
        Your plan unlocks after you have spoken with all three residents. The
        conversation is the research; the plan is the night.
      </p>
      <p className="mt-3 font-mono text-xs font-bold uppercase tracking-wider text-moss">
        {met}/3 residents met
      </p>
      <ul className="mt-3 grid grid-cols-3 gap-2">
        {(['mara', 'jun', 'theo'] as const).map((npcId) => {
          const npc = NPC_BY_ID[npcId];
          const isMet = state.interacted_npcs.includes(npcId);

          return (
            <li
              key={npcId}
              className={`border-2 px-2 py-2 text-center ${
                isMet
                  ? 'border-moss bg-moss/10'
                  : 'border-ink/20 bg-paper-light/50'
              }`}
            >
              <span className="block font-display text-lg font-bold leading-none">
                {npc.name}
              </span>
              <span className="mt-1 block font-mono text-[9px] font-bold uppercase tracking-wider text-ink/55">
                {isMet ? 'met' : 'waiting'}
              </span>
            </li>
          );
        })}
      </ul>
      <a href="#town-map" className="journal-button-secondary mt-4 inline-block">
        Back to the square
      </a>
    </section>
  );
}

function PlanPanel({
  state,
  stateToken,
  evaluation,
  onEvaluated,
  onRestart,
}: PlanPanelProps) {
  const [plan, setPlan] = useState<Plan>(() => state.plan ?? EMPTY_PLAN);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [lastPlan, setLastPlan] = useState<Plan | null>(null);

  if (state.stage === 'complete' || evaluation) {
    return (
      <EndingReport
        state={state}
        evaluation={evaluation}
        onRestart={onRestart}
      />
    );
  }

  if (state.stage !== 'plan') {
    return <PlanLocked state={state} />;
  }

  const update = (field: keyof Plan, value: string) => {
    setPlan((current) => ({ ...current, [field]: value }));
    setValidationError(null);
  };

  const runPlan = async (submitted: Plan) => {
    setPending(true);
    setError(null);

    try {
      const result = await evaluatePlan(state, stateToken, submitted);
      onEvaluated(result);
    } catch (requestError) {
      setError(requestError);
    } finally {
      setPending(false);
    }
  };

  const submit = () => {
    const trimmed: Plan = {
      movie: plan.movie.trim(),
      music: plan.music.trim(),
      food: plan.food.trim(),
      free_text: plan.free_text.trim(),
    };

    if (
      !trimmed.movie &&
      !trimmed.music &&
      !trimmed.food &&
      !trimmed.free_text
    ) {
      setValidationError(
        'Add a movie, soundtrack, menu, or a short note before sending the plan.',
      );
      return;
    }

    setValidationError(null);
    setLastPlan(trimmed);
    void runPlan(trimmed);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    submit();
  };

  const fields: Array<{
    field: 'movie' | 'music' | 'food';
    label: string;
    hint: string;
    placeholder: string;
  }> = [
    {
      field: 'movie',
      label: 'Movie',
      hint: 'What plays on the square?',
      placeholder: 'A film for the fountain',
    },
    {
      field: 'music',
      label: 'Music',
      hint: 'What carries the night?',
      placeholder: 'A record for the market',
    },
    {
      field: 'food',
      label: 'Food',
      hint: 'What feeds the crowd?',
      placeholder: 'A dish from the bakery',
    },
  ];

  return (
    <section className="paper-panel p-5" aria-labelledby="plan-heading">
      <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-tomato">
        Festival plan · unlocked
      </p>
      <h2
        id="plan-heading"
        className="mt-1 font-display text-3xl font-bold leading-tight"
      >
        Set the night
      </h2>
      <p className="mt-2 text-sm leading-6 text-ink/75">
        Turn what you heard into a movie, a soundtrack, and a menu. Add a note
        if the plan needs context. The backend judges the result and picks the
        ending.
      </p>

      <form onSubmit={handleSubmit} className="mt-4 space-y-3" noValidate>
        {fields.map((item) => (
          <div key={item.field}>
            <label
              htmlFor={`plan-${item.field}`}
              className="flex items-baseline justify-between gap-2"
            >
              <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em]">
                {item.label}
              </span>
              <span className="text-[10px] text-ink/55">{item.hint}</span>
            </label>
            <input
              id={`plan-${item.field}`}
              type="text"
              value={plan[item.field]}
              onChange={(event) => update(item.field, event.target.value)}
              maxLength={200}
              autoComplete="off"
              className="journal-input mt-1 w-full"
              placeholder={item.placeholder}
            />
          </div>
        ))}

        <div>
          <label
            htmlFor="plan-free-text"
            className="flex items-baseline justify-between gap-2"
          >
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.16em]">
              Field note · optional
            </span>
            <span className="text-[10px] text-ink/55">1000 max</span>
          </label>
          <textarea
            id="plan-free-text"
            value={plan.free_text}
            onChange={(event) => update('free_text', event.target.value)}
            maxLength={1000}
            rows={3}
            className="journal-input mt-1 w-full resize-y"
            placeholder="Why this combination belongs in the square tonight…"
          />
        </div>

        <p className="text-[11px] leading-5 text-ink/55">
          At least one field or a note is required. Your browser only sends the
          plan; it never calculates a score.
        </p>

        {validationError ? (
          <p
            role="alert"
            className="border-l-4 border-tomato bg-tomato/10 px-3 py-2 text-sm font-semibold text-tomato-dark"
          >
            {validationError}
          </p>
        ) : null}

        {error ? (
          <ErrorNotice
            error={error}
            context="plan"
            onRetry={lastPlan ? () => void runPlan(lastPlan) : undefined}
            retryLabel="Retry plan"
            onRestart={onRestart}
          />
        ) : null}

        <button
          type="submit"
          disabled={pending}
          className="journal-button flex w-full items-center justify-between disabled:cursor-wait disabled:opacity-65"
        >
          <span>{pending ? 'The town is deliberating…' : 'Send the plan'}</span>
          <span aria-hidden="true">→</span>
        </button>
      </form>
    </section>
  );
}

export default PlanPanel;
