import { describeApiError, type RecoveryContext } from '../api/errors';

interface ErrorNoticeProps {
  error: unknown;
  context: RecoveryContext;
  onRetry?: () => void;
  onRestart?: () => void;
  retryLabel?: string;
}

/**
 * Inline recovery message. It never blocks the panel's close button, so a
 * failed request cannot strand the player in an interaction.
 */
function ErrorNotice({
  error,
  context,
  onRetry,
  onRestart,
  retryLabel = 'Try again',
}: ErrorNoticeProps) {
  const guidance = describeApiError(error, context);
  const toneClasses =
    guidance.tone === 'danger'
      ? 'border-tomato/60 bg-tomato/10'
      : guidance.tone === 'warning'
        ? 'border-mustard/70 bg-mustard/15'
        : 'border-ink/25 bg-ink/5';

  return (
    <div
      role="alert"
      data-testid="api-error"
      className={`rounded-sm border-2 px-3 py-3 text-ink ${toneClasses}`}
    >
      <p className="font-mono text-[11px] font-bold uppercase tracking-[0.16em]">
        {guidance.title}
      </p>
      <p className="mt-1 text-sm leading-6">{guidance.message}</p>
      {onRetry && guidance.canRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-10 rounded-sm border-2 border-ink bg-paper-light px-3 py-1.5 font-mono text-xs font-bold uppercase tracking-wider text-ink shadow-[3px_3px_0_#2b2620] transition hover:bg-mustard focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tomato"
        >
          {retryLabel}
        </button>
      ) : null}
      {onRestart && guidance.needsRestart ? (
        <button
          type="button"
          onClick={onRestart}
          className="mt-3 ml-2 min-h-10 rounded-sm border-2 border-ink bg-tomato px-3 py-1.5 font-mono text-xs font-bold uppercase tracking-wider text-paper-light shadow-[3px_3px_0_#2b2620] transition hover:bg-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-tomato"
        >
          Start a new game
        </button>
      ) : null}
    </div>
  );
}

export default ErrorNotice;
