import test from 'node:test';
import assert from 'node:assert/strict';
import { createIdempotencyKey } from './idempotency.js';

test('uses the browser secure UUID API when available', () => {
  assert.equal(createIdempotencyKey({ randomUUID: () => 'secure-uuid' }), 'secure-uuid');
});

test('creates a v4 UUID from the secure random API on older browsers', () => {
  const key = createIdempotencyKey({ getRandomValues: (bytes) => bytes.fill(0) });
  assert.match(key, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test('fails safely when no cryptographically secure random source exists', () => {
  assert.throws(() => createIdempotencyKey({}), /Secure credit adjustments/);
});
