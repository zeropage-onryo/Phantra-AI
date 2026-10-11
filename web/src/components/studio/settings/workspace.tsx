"use client";

/* Settings → Workspace: the workspaces the person belongs to, and the
   switch between them. Membership is granted by members, never by signing
   up, so there is nothing to join from here. */
import { switchAccount } from "@/lib/studio-api";
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import {
  Badge,
  Button,
  EmptyState,
  Row,
  SectionHeader,
  SettingsCard,
  SkeletonRows,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "workspace")!;

export function WorkspaceSection() {
  const { me, toast } = useShell();
  const active = me?.account?.id;

  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard title="Your workspaces">
        {!me ? (
          <SkeletonRows rows={2} />
        ) : me.accounts.length === 0 ? (
          <EmptyState title="No workspace yet">
            Members are added by invitation, never by signing up. Ask the person who runs the workspace to add this
            address.
          </EmptyState>
        ) : (
          me.accounts.map((a) => (
            <Row
              key={a.id}
              label={
                <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
                  <span
                    aria-hidden
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      background: a.accent || "var(--edge-hi)",
                    }}
                  />
                  {a.label}
                  {a.id === active ? <Badge tone="ok">Active</Badge> : null}
                </span>
              }
              hint={a.role || "member"}
              control={
                a.id === active ? null : (
                  <Button
                    onClick={() =>
                      switchAccount(a.slug)
                        .then(() => window.location.reload())
                        .catch(() => toast("Could not switch workspace", "err"))
                    }
                  >
                    Switch
                  </Button>
                )
              }
            />
          ))
        )}
      </SettingsCard>
    </>
  );
}
