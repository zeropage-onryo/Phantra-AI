"use client";

import { Coins } from "lucide-react";
import { SECTIONS } from "@/lib/settings-sections";
import { EmptyState, SectionHeader, SettingsCard } from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "plan")!;

export function PlanSection() {
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard>
        <EmptyState icon={Coins} title="Your balance is on the credit pill">
          The pill in the header shows your credits, your plan and where to top up. This page is being built to hold all of it.
        </EmptyState>
      </SettingsCard>
    </>
  );
}
