/* "Notify me when a long job finishes" (2026-10-08): ONE preference, kept
   in this browser, with two switches on it since 2026-10-11 -- the
   activity tray's and Settings → Preferences'. Both read and write it
   here, and both hear the same event, so they cannot disagree.

   The browser's own permission is asked only on the click that turns it
   on. No "@/..." imports: this is plain browser code. */

export const NOTIFY_KEY = "zpf.notify";
export const NOTIFY_EVENT = "zpf:notify-pref";

/** subscribe to the preference (this tab's switches, and other tabs') */
export const subscribeNotify = (cb: () => void) => {
  window.addEventListener(NOTIFY_EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(NOTIFY_EVENT, cb);
    window.removeEventListener("storage", cb);
  };
};

export const readNotify = () => {
  try {
    return localStorage.getItem(NOTIFY_KEY) === "1";
  } catch {
    return false;
  }
};

/** this browser can show a notification at all */
export const canNotify = () => typeof window !== "undefined" && "Notification" in window;

/** Turn the preference on or off. Turning it on asks the browser for its
 *  permission first; "blocked" means the browser said no and nothing was
 *  changed. */
export async function setNotify(on: boolean): Promise<"on" | "off" | "blocked"> {
  if (on && canNotify() && Notification.permission !== "granted") {
    const answer = await Notification.requestPermission();
    if (answer !== "granted") return "blocked";
  }
  try {
    localStorage.setItem(NOTIFY_KEY, on ? "1" : "0");
  } catch {
    /* a private window forgets it */
  }
  window.dispatchEvent(new Event(NOTIFY_EVENT));
  return on ? "on" : "off";
}

/** what to say when the browser refused */
export const NOTIFY_BLOCKED = "Your browser is blocking notifications for this site";
