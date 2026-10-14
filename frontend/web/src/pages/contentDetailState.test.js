import test from 'node:test';
import assert from 'node:assert/strict';
import { findContent, getAuthorizedContent, getContentAccessError } from './contentDetailState.js';

test('content lookup safely handles absent rows and malformed API data', () => {
  assert.equal(findContent([], '2'), null);
  assert.equal(findContent([{ id: 1 }], '2'), null);
  assert.equal(findContent(null, '2'), null);
  assert.equal(findContent([{ id: 2, title: 'Notes' }], '2').title, 'Notes');
  assert.equal(findContent([{ id: 2 }], 'invalid'), null);
});

test('protected content contract accepts only recognized types and HTTPS URLs', () => {
  const result = getAuthorizedContent({ content: { id: 2, content_type: 'pdf', file_url: 'https://res.cloudinary.com/example.pdf?token=private' } });
  assert.equal(result.content_type, 'pdf');
  assert.throws(() => getAuthorizedContent({ content: { content_type: 'video', file_url: 'javascript:alert(1)' } }), /invalid|secure/i);
  assert.throws(() => getAuthorizedContent({ content: { content_type: 'ebook', file_url: 'https://example.com/file' } }), /valid protected resource/i);
  assert.throws(() => getAuthorizedContent({ content: { content_type: 'pdf', file_url: 'https://example.com/file' } }), /secure file-host/i);
  assert.throws(() => getAuthorizedContent({ content: { content_type: 'pdf', file_url: 'https://user:pass@res.cloudinary.com/file' } }), /secure file-host/i);
  assert.throws(() => getAuthorizedContent({ content: {} }), /valid protected resource/i);
});

test('access failures map to explicit user-facing states', () => {
  assert.equal(getContentAccessError({ status: 401 }).state, 'authentication-required');
  assert.equal(getContentAccessError({ status: 403 }).state, 'purchase-required');
  assert.equal(getContentAccessError({ status: 404 }).state, 'not-found');
  assert.equal(getContentAccessError(new TypeError('fetch failed')).state, 'network-error');
  assert.equal(getContentAccessError({ status: 500 }).state, 'access-denied');
});
