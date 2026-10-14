import test from 'node:test';
import assert from 'node:assert/strict';
import { countdownFor, estimateCredits, estimateRequiredCredits } from './useCountdown.js';

test('credit preview uses exact decimal integer arithmetic', () => {
  assert.equal(estimateCredits('100', '2.0000'), '50.00');
  assert.equal(estimateCredits('100', '0.5000'), '200.00');
  assert.equal(estimateCredits('100', '3.0000'), '33.33');
  assert.equal(estimateCredits('1.5', '2'), '0.75');
});

test('creator price preview rounds purchase credits up to avoid undercharging', () => {
  assert.equal(estimateRequiredCredits('100.50', '2'), '50.25');
  assert.equal(estimateRequiredCredits('100', '3'), '33.34');
});

test('countdown expires exactly at server-provided expiry time', () => {
  const now = Date.parse('2026-10-14T10:00:00Z');
  assert.deepEqual(countdownFor('2026-10-14T10:00:02Z', now), { seconds: 2, expired: false });
  assert.deepEqual(countdownFor('2026-10-14T10:00:00Z', now), { seconds: 0, expired: true });
});
