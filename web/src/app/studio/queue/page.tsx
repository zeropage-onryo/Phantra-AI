import { redirect } from "next/navigation";

/* The Queue is gone (2026-10-11, docs/tasks/task-higgsfield-shape.md,
   Mike's call: no idea board). It was where a picked scene waited for its
   priced approve. A scene is rendered from its own Render button now, and
   what is rendering or finished is listed on Renders. An old link lands
   there. */
export default function QueueRedirect() {
  redirect("/studio/renders");
}
