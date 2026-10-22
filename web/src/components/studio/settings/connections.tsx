"use client";

/* Settings → Connections: the person's own social accounts (2026-10-22,
   settings/social-accounts.tsx -- Instagram, Discord, more to come), then
   the addresses that connect an app to this studio (Connect MCP, 2026-10-16). The body is components/studio/
   connect-claude.tsx, the one source the account menus' dialog also draws.
   Connecting and disconnecting both happen in the app; this says where and
   deletes nothing, and nothing on this page spends.

   The "own model logins" card (a ChatGPT or Claude plan signed in on the
   server) is gone from the studio: only the classic studio's Guide ever
   used it, and its routes (app/model_connections.py) stay for that. */
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import { ConnectMcpBody } from "@/components/studio/connect-claude";
import { SocialAccounts } from "@/components/studio/settings/social-accounts";
import { SectionHeader, SettingsCard } from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "connections")!;

export function ConnectionsSection() {
  const { me, toast } = useShell();
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SocialAccounts />
      <SettingsCard title="Servers" description="paste the address into the app" pad>
        <ConnectMcpBody me={me} toast={toast} />
      </SettingsCard>
    </>
  );
}
