import test from 'node:test';
import assert from 'node:assert/strict';
import { createIdempotencyKey } from '../src/api/idempotency.js';

test('creates a UUID using secure random values on mobile', () => {
  const key = createIdempotencyKey({ getRandomValues: (bytes) => bytes.fill(0) });
  assert.match(key, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test('uses randomUUID when the runtime provides it', () => {
  assert.equal(createIdempotencyKey({ randomUUID: () => 'secure-mobile-uuid' }), 'secure-mobile-uuid');
});

test('fails safely when a secure random source is unavailable', () => {
  assert.throws(() => createIdempotencyKey({}), /Secure payment requests/);
});
