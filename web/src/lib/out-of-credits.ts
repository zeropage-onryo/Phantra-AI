/* A refusal for an empty balance, recognised (2026-10-11; the first item of
   the invideo list in docs/tasks/task-studio-agent.md).

   invideo's loudest complaint is the agent going quiet when the credits
   run out. Here the server already says so in a sentence of its own
   (src/charge.py `refusal`, `CREATE_REFUSAL`), but the page showed it as
   one more red line, with nothing to press. This is how any surface knows
   that line is THE one a person can fix by adding credits, and what the
   way out is called.

   The match is on plain phrases the server's own sentences contain, never
   on a provider's words: tests/test_out_of_credits.py reads PHRASES out of
   this file and holds every real refusal the server writes against it, so
   the two cannot drift apart silently.

   Pure and import-free: tests/out-of-credits.test.mjs runs it as it is. */

/** lower-case substrings; one is enough */
export const PHRASES = ["out of credits", "top up to continue", "subscribe or top up"];

/** Is this the studio saying the balance is too low? `status` is the HTTP
    status when the refusal came back from a route (402 is only ever that). */
export function needsCredits(text: string | null | undefined, status?: number): boolean {
  if (status === 402) return true;
  const said = (text ?? "").toLowerCase();
  return !!said && PHRASES.some((p) => said.includes(p));
}

/** "needs 10 and the account has 4" -> { needs: 10, has: 4 }; null when the
    sentence carries no numbers (a Create refused for having no plan). */
export function shortfall(text: string | null | undefined): { needs: number; has: number } | null {
  const m = /needs\s+([\d,]+)\s+and the account has\s+(-?[\d,]+)/i.exec(text ?? "");
  if (!m) return null;
  const n = (s: string) => Number(s.replace(/,/g, ""));
  return { needs: n(m[1]), has: n(m[2]) };
}

/** Where adding credits happens, and what the way there is called -- the
    credit pill's own words, so two doors onto one page read the same. */
export const TOP_UP_HREF = "/pricing";
export const topUpLabel = (account: { plan?: unknown; exempt?: boolean } | null | undefined): string =>
  account?.plan || account?.exempt ? "Buy credits" : "Choose a plan";

/** The one line a failed send's bubble says. */
export const NOT_SENT = "Not sent — try again";
export const NOT_SENT_CREDITS = "Not sent: you are out of credits";
