import type { Metadata } from "next";

export const metadata: Metadata = { title: "Create" };

/* /studio/new (2026-10-26): the compose page, where the phone's Create
   button goes -- the box alone, docked under a greeting. The (create)
   layout draws it (create-view.tsx reads the path); this page adds
   nothing. */
export default function CreateNew() {
  return null;
}
