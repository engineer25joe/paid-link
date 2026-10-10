import test from 'node:test';
import assert from 'node:assert/strict';
import { canAccessPath, dashboardPath, loginDestination, viewModeFor } from './navigation.js';

test('each role maps only to its own protected dashboard', () => {
  for (const role of ['learner', 'creator', 'admin']) {
    assert.equal(dashboardPath(role), `/${role}`);
    assert.equal(canAccessPath(`/${role}`, role), true);
    for (const other of ['learner', 'creator', 'admin'].filter((value) => value !== role)) {
      const adminMayUseCreatorTools = role === 'admin' && other === 'creator';
      assert.equal(canAccessPath(`/${other}`, role), adminMayUseCreatorTools);
    }
  }
  assert.equal(dashboardPath('unknown'), '/');
});

test('public destinations are valid and arbitrary or role-forbidden destinations are rejected', () => {
  for (const path of ['/', '/login', '/register', '/explore']) assert.equal(canAccessPath(path, 'learner'), true);
  assert.equal(canAccessPath('/admin/settings', 'admin'), false);
  assert.equal(canAccessPath('/admin/users', 'admin'), true);
  assert.equal(canAccessPath('https://example.com', 'admin'), false);
  assert.equal(canAccessPath('/creator/content/new', 'creator'), true);
  assert.equal(canAccessPath('/creator/content/new', 'admin'), true);
  assert.equal(canAccessPath('/creator/content/14/edit', 'creator'), true);
  assert.equal(canAccessPath('/creator/settings', 'creator'), false);
  assert.equal(canAccessPath('/admin/users', 'creator'), false);
  assert.equal(canAccessPath('/library', 'learner'), true);
  assert.equal(loginDestination('/admin', 'learner'), '/');
  assert.equal(loginDestination('/explore', 'creator'), '/explore');
  assert.equal(loginDestination('/login', 'admin'), '/');
  assert.equal(loginDestination(null, 'admin'), '/');
});

test('administrator display modes do not change non-admin role presentation', () => {
  assert.equal(viewModeFor('admin', 'creator'), 'creator');
  assert.equal(viewModeFor('admin', 'learner'), 'learner');
  assert.equal(viewModeFor('learner', 'admin'), 'learner');
  assert.equal(viewModeFor('creator', 'admin'), 'creator');
});
