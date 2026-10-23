import { Suspense } from "react";
import { LinkApp } from "@/components/studio/link-app";

/* /studio/link (2026-10-22, docs/tasks/task-premiere-plugin.md): where a
   Premiere Pro panel's sign-in code is approved. The panel opens this page
   with ?code=; a person can also type the code. */
export default function LinkPage() {
  return (
    <Suspense fallback={null}>
      <LinkApp />
    </Suspense>
  );
}
