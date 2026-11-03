import { PluginsPage } from "@/components/studio/plugins/plugins-page";

/* /studio/plugins (2026-10-23): the DaVinci Resolve panel and the Adobe
   panel (Premiere Pro and After Effects, one extension since 2026-11-03),
   where the Plugins flyout's rows open (#resolve, #premiere, #aftereffects). */
export default function Page() {
  return <PluginsPage />;
}
