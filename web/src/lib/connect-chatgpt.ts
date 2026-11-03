/* Phantra AI in ChatGPT's plugin directory (approved by OpenAI 2026-11-02, app
   asdk_app_6ad7a4325484819188bf181eeae543e2; the same listing covers Codex).

   Every "Connect to ChatGPT" button points here: /mcp's hero, its How to connect
   steps and closing buttons, the studio rail's Plugins flyout and the studio's
   Connect MCP panel. The listing's own Add button starts ChatGPT's sign-in to
   api.phantra.ai/mcp, so nothing is copied or pasted any more.

   higgsfield.ai/mcp adds `?open_in_app=1` to its listing link. Checked
   2026-11-02 in a signed-in browser: on the web it changes nothing (same page,
   same buttons), so the install link is the plain listing. */

/** the listing's permanent page on chatgpt.com */
export const CHATGPT_LISTING_URL =
  "https://chatgpt.com/plugins/plugin_asdk_app_6ad7a4325484819188bf181eeae543e2";

/** what a Connect button opens; one line to change if ChatGPT gains an install deep link */
export const CHATGPT_INSTALL_URL = CHATGPT_LISTING_URL;
