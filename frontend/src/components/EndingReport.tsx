import type {
  EvidenceStatus,
  GameState,
  PlanComponent,
  PlanEvaluateResponse,
  Ending,
} from '../api/types';
import { NPC_BY_ID } from '../game/npcs';

interface EndingReportProps {
  state: GameState;
  evaluation?: PlanEvaluateResponse;
  onRestart: () => void;
}

const COMPONENT_LABELS: Record<PlanComponent, string> = {
  movie: 'Movie',
  music: 'Music',
  food: 'Food',
};

const ENDING_PRESENTATION: Record<
  Ending,
  { title: string; kicker: string; description: string; className: string }
> = {
  perfect_harmony: {
    title: 'Perfect Harmony',
    kicker: 'The square finds its key',
    description:
      'Every corner of the plan answered another. The festival ends with one clear, generous note.',
    className: 'ending-perfect',
  },
  mixed_night: {
    title: 'Mixed Night',
    kicker: 'Rough edges, real stories',
    description:
      'Not every idea landed, but the square has enough warmth to carry the night.',
    className: 'ending-mixed',
  },
  cultural_chaos: {
    title: 'Cultural Chaos',
    kicker: 'The plot escapes the page',
    description:
      'The bill refused to behave. The town will remember it anyway — and start again.',
    className: 'ending-chaos',
  },
};

const EVIDENCE_STATUS_COPY: Record<
  EvidenceStatus,
  { label: string; detail: string }
> = {
  available: {
    label: 'Evidence available',
    detail: 'Every selected component had verified Qloo provenance.',
  },
  partial: {
    label: 'Partial evidence',
    detail:
      'Only part of the plan had verified Qloo provenance; missing pieces were not invented.',
  },
  unavailable: {
    label: 'Evidence unavailable',
    detail:
      'No verified Qloo evidence was available, so the backend scored the plan conservatively.',
  },
};

function EndingReport({ state, evaluation, onRestart }: EndingReportProps) {
  const ending = evaluation?.ending ?? state.ending;

  if (!ending) {
    return (
      <section className="paper-panel p-5 text-ink" aria-labelledby="ending-heading">
        <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-tomato">
          Field journal
        </p>
        <h2
          id="ending-heading"
          className="mt-1 font-display text-2xl font-bold"
        >
          No ending recorded
        </h2>
        <p className="mt-2 text-sm leading-6 text-ink/70">
          This saved game has no completed ending. Start a new game to plan
          another festival night.
        </p>
        <button type="button" onClick={onRestart} className="journal-button mt-4">
          Start a new game
        </button>
      </section>
    );
  }

  const presentation = ENDING_PRESENTATION[ending];
  const score = evaluation?.score ?? state.score;
  const evidenceStatus =
    evaluation?.evidence_status ??
    (state.cultural_matches === null ? 'unavailable' : null);
  const statusCopy = evidenceStatus
    ? EVIDENCE_STATUS_COPY[evidenceStatus]
    : null;

  return (
    <section
      aria-labelledby="ending-heading"
      className={`paper-panel ending-sheet p-5 text-ink ${presentation.className}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.18em]">
            Festival result · field journal
          </p>
          <p className="mt-1 font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-ink/55">
            {presentation.kicker}
          </p>
        </div>
        <div className="ending-stamp" aria-hidden="true">
          {ending === 'perfect_harmony'
            ? 'In tune'
            : ending === 'mixed_night'
              ? 'Almost'
              : 'Again!'}
        </div>
      </div>

      <h2
        id="ending-heading"
        className="mt-4 font-display text-4xl font-bold leading-[0.95] tracking-[-0.03em]"
      >
        {presentation.title}
      </h2>
      <p className="mt-3 text-sm leading-6 text-ink/80">
        {presentation.description}
      </p>

      <div className="mt-4 flex items-end justify-between gap-3 border-y-2 border-ink/25 py-3">
        <div>
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-ink/55">
            Server score
          </p>
          <p
            data-testid="ending-score"
            className="font-display text-4xl font-bold leading-none"
          >
            {score === null ? '—' : score}
            <span className="font-mono text-sm font-normal text-ink/50">/100</span>
          </p>
        </div>
        <p className="max-w-[11rem] text-right text-[11px] leading-5 text-ink/60">
          Score and ending come from the backend rules engine, never this
          browser.
        </p>
      </div>

      {evaluation ? (
        <p className="mt-3 text-sm leading-6 text-ink/75">{evaluation.analysis}</p>
      ) : (
        <p className="mt-3 text-sm leading-6 text-ink/70">
          This is a resumed ending. The signed result is intact; detailed
          evidence from the original evaluation was not stored in this browser.
        </p>
      )}

      {statusCopy ? (
        <div className="mt-4 border-2 border-ink/20 bg-paper-light/70 px-3 py-2">
          <p className="font-mono text-[10px] font-bold uppercase tracking-[0.15em]">
            {statusCopy.label}
          </p>
          <p className="mt-1 text-xs leading-5 text-ink/70">
            {statusCopy.detail}
          </p>
        </div>
      ) : null}

      {evaluation ? (
        <>
          <div className="mt-5">
            <h3 className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-tomato">
              Component reasons
            </h3>
            <div className="mt-2 space-y-2">
              {evaluation.components.map((component) => (
                <details
                  key={component.component}
                  className="border border-ink/20 bg-paper-light/60 px-3 py-2"
                >
                  <summary className="cursor-pointer font-mono text-[11px] font-bold uppercase tracking-wide">
                    {COMPONENT_LABELS[component.component]} ·{' '}
                    {component.score}/100 ·{' '}
                    {component.evidence_available ? 'evidenced' : 'no evidence'}
                  </summary>
                  <p className="mt-2 text-xs leading-5 text-ink/70">
                    Plan: {component.plan_value || '—'} ·{' '}
                    {component.evidence_count} Qloo item(s)
                  </p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-5 text-ink/70">
                    {component.reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </details>
              ))}
            </div>
          </div>

          <div className="mt-5">
            <h3 className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-tomato">
              Resident reactions
            </h3>
            <div className="mt-2 space-y-2">
              {evaluation.reactions.map((reaction) => (
                <blockquote
                  key={reaction.npc_id}
                  className="border-l-4 border-ink/40 bg-paper-light/60 px-3 py-2"
                >
                  <p className="font-mono text-[10px] font-bold uppercase tracking-wide">
                    {reaction.name} · rapport {reaction.relationship} · NPC score{' '}
                    {reaction.npc_score}
                  </p>
                  <p className="mt-1 text-sm leading-6">{reaction.reaction}</p>
                </blockquote>
              ))}
            </div>
          </div>

          <div className="mt-5">
            <h3 className="font-mono text-[10px] font-bold uppercase tracking-[0.18em] text-tomato">
              Evidence ledger · {evaluation.evidence.length}
            </h3>
            {evaluation.evidence.length === 0 ? (
              <p className="mt-2 border-l-2 border-tomato/50 bg-tomato/5 px-3 py-2 text-xs leading-5">
                The ledger is empty. No Qloo entity was invented to fill it,
                and the backend used its conservative empty-evidence score.
              </p>
            ) : (
              <ul className="mt-2 space-y-1.5">
                {evaluation.evidence.map((item, index) => (
                  <li
                    key={`${item.component}-${item.npc_id}-${item.entity_id ?? item.tag_id ?? index}`}
                    className="border-l-2 border-moss/60 bg-moss/5 px-2 py-1.5"
                  >
                    <p className="text-xs font-bold">
                      {item.label || 'Unlabelled Qloo evidence'} ·{' '}
                      {COMPONENT_LABELS[item.component]}
                    </p>
                    <p className="mt-0.5 break-all font-mono text-[10px] text-ink/50">
                      {NPC_BY_ID[item.npc_id].name} · {item.query_type || 'qloo'} ·{' '}
                      {item.entity_id ?? item.tag_id ?? '—'}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <details className="mt-5 border-t-2 border-ink/20 pt-3">
            <summary className="cursor-pointer font-mono text-[10px] font-bold uppercase tracking-[0.16em] text-ink/65">
              Full rules notes
            </summary>
            <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-5 text-ink/70">
              {evaluation.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
              {evaluation.npcs.map((npc) => (
                <li key={npc.npc_id}>{npc.reasons.join(' ')}</li>
              ))}
            </ul>
          </details>
        </>
      ) : null}

      <div className="mt-5 flex flex-wrap gap-2">
        <button type="button" onClick={onRestart} className="journal-button">
          Plan another night
        </button>
        <a href="#town-map" className="journal-button-secondary">
          Back to the square
        </a>
      </div>
    </section>
  );
}

export default EndingReport;
