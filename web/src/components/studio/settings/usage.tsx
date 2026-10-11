"use client";

import { ChartNoAxesColumn } from "lucide-react";
import { SECTIONS } from "@/lib/settings-sections";
import { EmptyState, SectionHeader, SettingsCard } from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "usage")!;

export function UsageSection() {
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard>
        <EmptyState icon={ChartNoAxesColumn} title="No history to show yet">
          Every hold, charge and grant on this workspace will be listed here.
        </EmptyState>
      </SettingsCard>
    </>
  );
}
