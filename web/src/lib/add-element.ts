/* The new-element modal's spend, as pure functions (QA 2026-11-02 T10).

   The reference sheet is a paid still, so it is OFF until the person ticks
   it (it used to start ticked, and a form that left `sheet` out drew one on
   the server too), and the button that spends says what it spends: "Add"
   saves for free, "Add · 10 credits" saves and draws. */

/** the sheet box's starting state: never pre-ticked */
export const SHEET_BY_DEFAULT = false;

/** the modal's one button; `price` is the sheet's creditsText, or null
 *  until the balance has answered */
export function addLabel(busy: boolean, willDraw: boolean, price: string | null): string {
  if (busy) return "Saving…";
  if (!willDraw || !price) return "Add";
  return `Add · ${price}`;
}
