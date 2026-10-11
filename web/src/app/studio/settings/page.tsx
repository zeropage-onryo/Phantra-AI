import { redirect } from "next/navigation";
import { settingsTarget } from "@/lib/settings-sections";

/* /studio/settings was one page until 2026-10-11; it is an area of six
   sections now, and the old address opens the first of them. */
export default function SettingsIndex() {
  redirect(settingsTarget());
}
