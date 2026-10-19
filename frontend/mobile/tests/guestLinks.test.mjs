import test from 'node:test';
import assert from 'node:assert/strict';
import { createGuestLinking, parseGuestLink, requestErrorScreen, shareStateScreen } from '../src/navigation/guestLinks.mjs';

test('app launch with no initial URL starts without guest routing', () => {
  assert.deepEqual(parseGuestLink(null), { type: 'none' });
  assert.deepEqual(parseGuestLink(undefined), { type: 'none' });
  assert.deepEqual(parseGuestLink(''), { type: 'none' });
});
test('navigation linking returns no initial route for ordinary launch or unrelated URL', async () => {
  const noLink = createGuestLinking(async () => null, () => () => {});
  const unrelated = createGuestLinking(async () => 'https://paidlinkweb.onrender.com/explore', () => () => {});
  assert.equal(await noLink.getInitialURL(), null);
  assert.equal(await unrelated.getInitialURL(), null);
});
test('valid web and Android guest share links are recognized', () => {
  assert.deepEqual(parseGuestLink('https://paidlinkweb.onrender.com/shared/secret-token'), { type: 'share', token: 'secret-token' });
  assert.deepEqual(parseGuestLink('paidlink://shared/secret-token'), { type: 'share', token: 'secret-token' });
});
test('malformed share link with an empty token is invalid', () => {
  assert.deepEqual(parseGuestLink('https://paidlinkweb.onrender.com/shared/'), { type: 'malformed', kind: 'shared' });
});
test('backend share states map to their specific screens', () => {
  assert.equal(shareStateScreen({ status: 'ACTIVE' }), 'active');
  assert.equal(shareStateScreen({ status: 'EXPIRED' }), 'expired');
  assert.equal(shareStateScreen({ status: 'REVOKED' }), 'revoked');
  assert.equal(shareStateScreen({ status: 'LIMIT REACHED' }), 'limit');
});
test('backend rejected and unavailable link checks remain distinct', () => {
  assert.equal(requestErrorScreen({ status: 404 }), 'invalid');
  assert.equal(requestErrorScreen({ status: 410 }), 'expired');
  assert.equal(requestErrorScreen({ status: 503 }), 'network');
  assert.equal(requestErrorScreen(new Error('offline')), 'network');
});
test('unrelated URL is ignored', () => {
  assert.deepEqual(parseGuestLink('https://paidlinkweb.onrender.com/explore'), { type: 'unrelated' });
  assert.deepEqual(parseGuestLink('https://example.com/shared/secret-token'), { type: 'unrelated' });
});
