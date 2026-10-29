import type {
  ApiErrorEnvelope,
  DialogueResponse,
  DialogueTurn,
  GameState,
  Plan,
  PlanEvaluateResponse,
  PlayerInterests,
  StartGameResponse,
} from './types';
import type { NpcId } from '../game/types';

const DEFAULT_DEV_API_ORIGIN = 'http://127.0.0.1:8000';
const REQUEST_TIMEOUT_MS = 30_000;

/**
 * Resolve the API origin at runtime.
 *
 * Local Vite defaults to the local FastAPI port. Production builds use a
 * same-origin deployment unless `VITE_API_BASE_URL` explicitly points at a
 * separate API host, so no localhost URL is baked into a production bundle.
 */
export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();

  if (configured) {
    return configured.replace(/\/+$/, '');
  }

  return import.meta.env.DEV ? DEFAULT_DEV_API_ORIGIN : '';
}

/**
 * A safe, client-facing request failure.
 *
 * `code` comes from the backend error envelope when available. The UI maps
 * status/code pairs to recovery actions; it never parses provider details.
 */
export class ApiRequestError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly retryable: boolean;

  constructor(
    message: string,
    options: {
      status?: number | null;
      code?: string;
      retryable?: boolean;
      cause?: unknown;
    } = {},
  ) {
    super(message, { cause: options.cause });
    this.name = 'ApiRequestError';
    this.status = options.status ?? null;
    this.code = options.code ?? 'request_failed';
    this.retryable = options.retryable ?? false;
  }
}

function isErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const candidate = value as {
    error?: { code?: unknown; message?: unknown; retryable?: unknown };
  };

  return (
    typeof candidate.error?.code === 'string' &&
    typeof candidate.error.message === 'string' &&
    typeof candidate.error.retryable === 'boolean'
  );
}

function fallbackMessage(status: number): string {
  if (status === 401) {
    return 'Your game session expired. Start a new game to continue.';
  }
  if (status === 402) {
    return 'The town services are currently unavailable.';
  }
  if (status === 409) {
    return 'This saved game could not be verified. Start a new game to continue.';
  }
  if (status === 429) {
    return 'The town is busy right now. Wait a moment and try again.';
  }
  if (status >= 500) {
    return 'A town service is taking a break. Please try again.';
  }
  return 'The request could not be completed.';
}

async function readResponseJson(response: Response): Promise<unknown> {
  const text = await response.text();

  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return null;
  }
}

async function request<T>(
  path: string,
  init: RequestInit,
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;

  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...init.headers,
      },
      signal: controller.signal,
    });
  } catch (error) {
    const aborted =
      error instanceof DOMException && error.name === 'AbortError';

    throw new ApiRequestError(
      aborted
        ? 'The request took too long. Check your connection and try again.'
        : 'Could not reach the town service. Check your connection and try again.',
      {
        code: aborted ? 'request_timeout' : 'network_error',
        retryable: true,
        cause: error,
      },
    );
  } finally {
    clearTimeout(timeout);
  }

  const body = await readResponseJson(response);

  if (!response.ok) {
    if (isErrorEnvelope(body)) {
      throw new ApiRequestError(body.error.message, {
        status: response.status,
        code: body.error.code,
        retryable: body.error.retryable,
      });
    }

    throw new ApiRequestError(fallbackMessage(response.status), {
      status: response.status,
      code: `http_${response.status}`,
      retryable:
        response.status === 429 || response.status >= 500,
    });
  }

  if (body === null) {
    throw new ApiRequestError(
      'The town service returned an empty response. Please try again.',
      {
        status: response.status,
        code: 'invalid_response',
        retryable: true,
      },
    );
  }

  return body as T;
}

export function startGame(
  playerInterests: PlayerInterests,
): Promise<StartGameResponse> {
  return request<StartGameResponse>('/api/game/start', {
    method: 'POST',
    body: JSON.stringify({ player_interests: playerInterests }),
  });
}

export function sendDialogue(
  npcId: NpcId,
  state: GameState,
  stateToken: string,
  message: string,
  conversation: DialogueTurn[],
): Promise<DialogueResponse> {
  return request<DialogueResponse>(`/api/npc/${npcId}/dialogue`, {
    method: 'POST',
    body: JSON.stringify({
      state,
      state_token: stateToken,
      message,
      conversation: conversation.slice(-8),
    }),
  });
}

export function evaluatePlan(
  state: GameState,
  stateToken: string,
  plan: Plan,
): Promise<PlanEvaluateResponse> {
  return request<PlanEvaluateResponse>('/api/plan/evaluate', {
    method: 'POST',
    body: JSON.stringify({
      state,
      state_token: stateToken,
      plan,
    }),
  });
}
