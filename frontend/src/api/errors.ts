import { ApiRequestError } from './client';

export type RecoveryContext = 'start' | 'dialogue' | 'plan';

export interface RecoveryGuidance {
  title: string;
  message: string;
  canRetry: boolean;
  needsRestart: boolean;
  tone: 'warning' | 'danger' | 'neutral';
}

const STATE_ERROR_CODES = new Set([
  'state_integrity_error',
  'invalid_state',
  'state_token_invalid',
  'state_token_expired',
  'stage_prerequisite',
]);

function opening(context: RecoveryContext): string {
  if (context === 'start') {
    return 'Could not open the festival';
  }
  if (context === 'dialogue') {
    return 'Conversation paused';
  }
  return 'The plan was not submitted';
}

/**
 * Turn a request failure into plain-language recovery guidance.
 *
 * No provider or server internals are shown. State-integrity failures point to
 * a restart because the signed token can no longer be repaired client-side.
 */
export function describeApiError(
  error: unknown,
  context: RecoveryContext = 'plan',
): RecoveryGuidance {
  const title = opening(context);

  if (!(error instanceof ApiRequestError)) {
    return {
      title,
      message:
        'Something unexpected interrupted the request. You can try again without losing your place.',
      canRetry: true,
      needsRestart: false,
      tone: 'warning',
    };
  }

  if (STATE_ERROR_CODES.has(error.code)) {
    return {
      title: 'This saved game is out of date',
      message:
        'The signed game state could not be verified. Start a new game to return to the square.',
      canRetry: false,
      needsRestart: true,
      tone: 'danger',
    };
  }

  if (error.status === 401) {
    return {
      title: 'Your session has ended',
      message:
        'The town no longer recognises this game session. Start a new game to keep playing.',
      canRetry: false,
      needsRestart: true,
      tone: 'danger',
    };
  }

  if (error.status === 402) {
    return {
      title: 'Town services are unavailable',
      message:
        'This feature is not currently available. You can close this panel and keep exploring the square.',
      canRetry: false,
      needsRestart: false,
      tone: 'warning',
    };
  }

  if (error.status === 429) {
    return {
      title: 'The square is busy',
      message:
        'Too many requests are arriving at once. Wait a moment, then try this step again.',
      canRetry: true,
      needsRestart: false,
      tone: 'warning',
    };
  }

  if (error.status !== null && error.status >= 500) {
    return {
      title:
        context === 'plan'
          ? 'The judges need a moment'
          : 'A town service is taking a break',
      message:
        'The request could not be completed, but your signed progress is safe. Try again in a moment.',
      canRetry: true,
      needsRestart: false,
      tone: 'warning',
    };
  }

  if (error.code === 'network_error' || error.code === 'request_timeout') {
    return {
      title: 'Cannot reach the town',
      message:
        'Check your connection and that the API is running, then retry. Your saved game is still on this device.',
      canRetry: true,
      needsRestart: false,
      tone: 'warning',
    };
  }

  return {
    title,
    message: error.message,
    canRetry: error.retryable,
    needsRestart: false,
    tone: error.retryable ? 'warning' : 'neutral',
  };
}
