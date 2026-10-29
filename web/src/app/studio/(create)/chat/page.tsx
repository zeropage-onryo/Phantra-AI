import type { Metadata } from "next";

export const metadata: Metadata = { title: "Chat" };

/* /studio/chat: the open conversation. The (create) layout draws it (the
   thread and the docked box); this page adds nothing. */
export default function CreateChat() {
  return null;
}
