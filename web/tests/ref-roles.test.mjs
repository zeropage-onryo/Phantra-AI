import { test } from 'node:test';
import assert from 'node:assert/strict';
import { setRole, rolesFor, roleLabel, asRoles, refKey } from '../src/lib/ref-roles.ts';

const OPTIONS = [
  { id: 'subject', label: 'Subject', look_only: false },
  { id: 'product', label: 'Product', look_only: false },
  { id: 'light', label: 'Light', look_only: true },
];

test('a role is put on a reference and taken off again', () => {
  let roles = setRole(null, '/refs/a.jpg?thumb=1', 'light');
  assert.deepEqual(roles, { '/refs/a.jpg': 'light' });
  roles = setRole(roles, '/refs/b.jpg', 'product');
  roles = setRole(roles, '/refs/a.jpg', 'subject');           // changed, not doubled
  assert.deepEqual(roles, { '/refs/a.jpg': 'subject', '/refs/b.jpg': 'product' });
  assert.deepEqual(setRole(roles, '/refs/a.jpg', null), { '/refs/b.jpg': 'product' });
  assert.deepEqual(setRole(roles, '/refs/b.jpg', ''), { '/refs/a.jpg': 'subject' });
  assert.equal(refKey('/refs/a.jpg?x=1'), '/refs/a.jpg');
});

test('what is sent is the roles of what is attached, and only roles there are', () => {
  const roles = { '/refs/a.jpg': 'light', '/refs/gone.jpg': 'product', '/refs/c.jpg': 'vibes' };
  assert.deepEqual(rolesFor(roles, ['/refs/a.jpg', '/refs/c.jpg', '/refs/d.jpg'], OPTIONS), { '/refs/a.jpg': 'light' });
  assert.deepEqual(rolesFor(roles, [], OPTIONS), {});
  assert.deepEqual(rolesFor(null, ['/refs/a.jpg'], OPTIONS), {});
  // with no menu from the server, nothing is claimed
  assert.deepEqual(rolesFor(roles, ['/refs/a.jpg'], []), {});
});

test('the chip says the role in the server\'s word', () => {
  const roles = { '/refs/a.jpg': 'light' };
  assert.equal(roleLabel(roles, '/refs/a.jpg?thumb=1', OPTIONS), 'Light');
  assert.equal(roleLabel(roles, '/refs/b.jpg', OPTIONS), '');
  assert.equal(roleLabel({ '/refs/a.jpg': 'vibes' }, '/refs/a.jpg', OPTIONS), '');
});

test('a saved map that came back wrong is no roles, never a crash', () => {
  assert.deepEqual(asRoles({ '/refs/a.jpg': 'light', '/refs/b.jpg': 3, '': 'light' }), { '/refs/a.jpg': 'light' });
  for (const junk of [null, undefined, 'x', 5, ['light']]) assert.deepEqual(asRoles(junk), {});
});
