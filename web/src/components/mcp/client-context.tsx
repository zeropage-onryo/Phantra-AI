"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

// Which client the page is showing (Claude, ChatGPT, ...). The hero's pills and
// the setup steps below it read and set the same one, and it lives in the URL
// hash (#claude, #chatgpt, ...) so a link can open the right one.

type Ctx = { active: string; setActive: (id: string) => void };
const McpClientContext = createContext<Ctx | null>(null);

export function McpClientProvider({ ids, children }: { ids: string[]; children: ReactNode }) {
  const [active, setActiveState] = useState(ids[0]);

  // follow the hash: a pasted link, the back button, a "#claude" anchor
  useEffect(() => {
    const read = () => {
      const id = window.location.hash.replace("#", "");
      if (ids.includes(id)) setActiveState(id);
    };
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, [ids]);

  const setActive = useCallback((id: string) => {
    setActiveState(id);
    try {
      window.history.replaceState(null, "", `#${id}`);
    } catch {
      /* the pick still works without the hash */
    }
  }, []);

  return <McpClientContext.Provider value={{ active, setActive }}>{children}</McpClientContext.Provider>;
}

/** The page-wide pick when a provider wraps the page; null on a page without one. */
export function useMcpClientOptional(): Ctx | null {
  return useContext(McpClientContext);
}
