import { CreateView } from "./create-view";

/* Create's two addresses, one composer (2026-10-22): /studio is the home
   (the box and the sections under it) and /studio/chat is the open
   conversation. The composer lives HERE, in the layout both pages share,
   so moving between them never unmounts it: a send started on the home
   keeps its wait, its progress line and its job when the address moves to
   the chat. The pages themselves draw nothing (create-view.tsx reads the
   path to decide which view it is). */
export default function CreateLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <CreateView />
      {children}
    </>
  );
}
