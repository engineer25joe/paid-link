import test from 'node:test';
import assert from 'node:assert/strict';
import { canAccessPath, dashboardPath, loginDestination } from './navigation.js';

test('each role maps only to its own protected dashboard', () => {
  for (const role of ['learner', 'creator', 'admin']) {
    assert.equal(dashboardPath(role), `/${role}`);
    assert.equal(canAccessPath(`/${role}`, role), true);
    for (const other of ['learner', 'creator', 'admin'].filter((value) => value !== role)) assert.equal(canAccessPath(`/${other}`, role), false);
  }
  assert.equal(dashboardPath('unknown'), '/');
});

test('public destinations are valid and arbitrary or role-forbidden destinations are rejected', () => {
  for (const path of ['/', '/login', '/register', '/explore']) assert.equal(canAccessPath(path, 'learner'), true);
  assert.equal(canAccessPath('/admin/settings', 'admin'), false);
  assert.equal(canAccessPath('https://example.com', 'admin'), false);
  assert.equal(loginDestination('/admin', 'learner'), '/learner');
  assert.equal(loginDestination('/explore', 'creator'), '/explore');
  assert.equal(loginDestination(null, 'admin'), '/admin');
});
