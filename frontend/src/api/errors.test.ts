import { describe, expect, it } from 'vitest';

import { ApiRequestError } from './client';
import { describeApiError } from './errors';

describe('describeApiError', () => {
  it.each([
    [401, 'unauthorized', true, false],
    [402, 'payment_required', false, false],
    [429, 'rate_limited', false, true],
    [500, 'internal_error', false, true],
    [503, 'service_unavailable', false, true],
  ])(
    'maps HTTP %s to recovery guidance',
    (status, code, needsRestart, canRetry) => {
      const guidance = describeApiError(
        new ApiRequestError('safe message', {
          status,
          code,
          retryable: canRetry,
        }),
        'dialogue',
      );

      expect(guidance.needsRestart).toBe(needsRestart);
      expect(guidance.canRetry).toBe(canRetry);
      expect(guidance.message).not.toMatch(/stack|trace/i);
    },
  );

  it('treats a signed-state rejection as a restart requirement', () => {
    const guidance = describeApiError(
      new ApiRequestError('invalid signature', {
        status: 409,
        code: 'state_integrity_error',
        retryable: false,
      }),
      'plan',
    );

    expect(guidance.needsRestart).toBe(true);
    expect(guidance.canRetry).toBe(false);
    expect(guidance.title).toBe('This saved game is out of date');
  });

  it('keeps network failures retryable and never drops the save', () => {
    const guidance = describeApiError(
      new ApiRequestError('offline', {
        code: 'network_error',
        retryable: true,
      }),
      'start',
    );

    expect(guidance.canRetry).toBe(true);
    expect(guidance.needsRestart).toBe(false);
    expect(guidance.title).toBe('Cannot reach the town');
  });

  it('falls back safely for an unknown thrown value', () => {
    const guidance = describeApiError(new Error('boom'), 'plan');

    expect(guidance.canRetry).toBe(true);
    expect(guidance.needsRestart).toBe(false);
    expect(guidance.message).not.toContain('boom');
  });
});
