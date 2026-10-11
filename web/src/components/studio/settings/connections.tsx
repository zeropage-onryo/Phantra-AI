"use client";

import { Plug } from "lucide-react";
import { SECTIONS } from "@/lib/settings-sections";
import { EmptyState, SectionHeader, SettingsCard } from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "connections")!;

export function ConnectionsSection() {
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard>
        <EmptyState icon={Plug} title="Connect to Claude is in the account menu">
          Open the menu on your avatar and choose Connect to Claude. This page is being built to hold it.
        </EmptyState>
      </SettingsCard>
    </>
  );
}
