import { SettingsFrame } from "@/components/studio/settings/frame";

/* The settings AREA (2026-10-11, docs/tasks/task-settings-page.md): one
   frame -- the section nav -- around six sections, each its own URL under
   /studio/settings/. The pages are thin; the sections live in
   components/studio/settings/. */
export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return <SettingsFrame>{children}</SettingsFrame>;
}
