/* A resolve hook for node's own type stripping (tests/create-v2.test.mjs):
   a component file written for Next imports its neighbours without an
   extension ("../../../lib/create-v2"), which node's ESM loader refuses.
   This tries the same specifier with ".ts" when the bare one is not
   found. Registered by the test that needs it (node:module register), so
   `node --test tests/*.test.mjs` stays the one command. */
export async function resolve(specifier, context, next) {
  if (specifier.startsWith('.') && !/\.[a-z]+$/i.test(specifier)) {
    try {
      return await next(`${specifier}.ts`, context);
    } catch {
      /* fall through to the plain resolution */
    }
  }
  return next(specifier, context);
}
