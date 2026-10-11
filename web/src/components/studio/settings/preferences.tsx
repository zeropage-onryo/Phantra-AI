"use client";

import { SlidersHorizontal } from "lucide-react";
import { SECTIONS } from "@/lib/settings-sections";
import { EmptyState, SectionHeader, SettingsCard } from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "preferences")!;

export function PreferencesSection() {
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard>
        <EmptyState icon={SlidersHorizontal} title="Nothing to set here yet">
          Your generation defaults live on the Create box, and notifications on the activity bell, for now.
        </EmptyState>
      </SettingsCard>
    </>
  );
}
