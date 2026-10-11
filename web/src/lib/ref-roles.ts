/* What each attached reference is FOR (item 8 of
   docs/tasks/task-studio-agent.md; src/ref_roles.py is the rule).

   The roles themselves are the server's (GET /api/ref-roles) -- this file
   knows no role by name. It only keeps the map the box holds honest:
   `{url: role}`, for the references that are attached and nothing else.

   Pure and import-free: tests/ref-roles.test.mjs runs it as it is. */

export type RoleOption = { id: string; label: string; look_only: boolean };
export type Roles = Record<string, string>;

/** a reference as the map is keyed by: its address without a query */
export const refKey = (url: string) => url.split("?")[0];

/** Put a role on a reference, or take it off (null / ""). */
export function setRole(roles: Roles | null | undefined, url: string, role: string | null): Roles {
  const next = { ...(roles ?? {}) };
  if (role) next[refKey(url)] = role;
  else delete next[refKey(url)];
  return next;
}

/** The roles of exactly these references, held to the roles there are: what
    is sent with a request and saved with the box. A role for a picture
    that is no longer attached, or one the server does not offer, is gone. */
export function rolesFor(roles: Roles | null | undefined, attached: string[], options: RoleOption[]): Roles {
  const known = new Set(options.map((o) => o.id));
  const out: Roles = {};
  for (const url of attached) {
    const role = (roles ?? {})[refKey(url)];
    if (role && known.has(role)) out[refKey(url)] = role;
  }
  return out;
}

/** What the chip says: the role's own word, or "" when it has none. */
export const roleLabel = (roles: Roles | null | undefined, url: string, options: RoleOption[]): string =>
  options.find((o) => o.id === (roles ?? {})[refKey(url)])?.label ?? "";

/** whatever came back from storage, as a map of strings */
export function asRoles(raw: unknown): Roles {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const out: Roles = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof v === "string" && v && k) out[k] = v;
  }
  return out;
}
