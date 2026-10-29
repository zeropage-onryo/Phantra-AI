"use client";

import { useEffect } from "react";
import { cleanRef, refCookie, reportRef } from "@/lib/affiliate";

// A visit to phantra.ai/?ref=<code> remembers the code for 60 days
// (src/affiliates.py reads the cookie when the person signs up). Renders
// nothing; does nothing without a valid ?ref=. The query stays in the URL.
export function RefCapture() {
  useEffect(() => {
    try {
      const code = cleanRef(new URLSearchParams(window.location.search).get("ref"));
      if (code) {
        document.cookie = refCookie(code, window.location.hostname, window.location.protocol === "https:");
        // already signed in with a brand-new workspace? the server attributes it; otherwise it ignores this
        void reportRef(code);
      }
    } catch {
      // cookies blocked -- attribution just does not happen
    }
  }, []);
  return null;
}
