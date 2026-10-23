"use client";

/* Settings → Connect MCP (was Connections; 2026-10-16): the addresses that
   connect an app to this studio. The body is components/studio/
   connect-claude.tsx, the one source the account menus' dialog also draws.
   Connecting and disconnecting a connector both happen in the app; this
   says where and deletes nothing, and nothing on this page spends.

   Apps (2026-10-22, app/plugin_api.py): the editing-app panels this person
   signed in with a code (Premiere Pro), each with Disconnect, which stops
   that copy's token at once. A panel is connected from /studio/link.

   The "own model logins" card (a ChatGPT or Claude plan signed in on the
   server) is gone from the studio: only the classic studio's Guide ever
   used it, and its routes (app/model_connections.py) stay for that. */
import { useEffect, useState } from "react";
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import { ConnectMcpBody } from "@/components/studio/connect-claude";
import { Button, EmptyState, Row, SectionHeader, SettingsCard } from "@/components/studio/settings/ui";
import { listPluginConnections, revokePluginConnection, type PluginConnection } from "@/lib/studio-api";

const SECTION = SECTIONS.find((s) => s.id === "connections")!;

function when(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function Apps() {
  const { toast } = useShell();
  const [items, setItems] = useState<PluginConnection[] | null>(null);
  const [busy, setBusy] = useState<number | null>(null);

  useEffect(() => {
    listPluginConnections()
      .then((r) => setItems(r.items))
      .catch(() => setItems([]));
  }, []);

  const disconnect = async (c: PluginConnection) => {
    setBusy(c.id);
    try {
      await revokePluginConnection(c.id);
      setItems((now) => (now || []).filter((x) => x.id !== c.id));
      toast(`${c.client} disconnected`);
    } catch {
      toast("Couldn't disconnect. Try again.", "err");
    } finally {
      setBusy(null);
    }
  };

  return (
    <SettingsCard title="Apps" description="editing apps signed in with a code">
      {items === null ? null : items.length === 0 ? (
        <EmptyState title="No apps connected">
          Open the Phantra panel in DaVinci Resolve or Premiere Pro and choose Sign in. It shows a code to approve at phantra.ai/studio/link.
        </EmptyState>
      ) : (
        items.map((c) => (
          <Row
            key={c.id}
            label={c.device ? `${c.client} · ${c.device}` : c.client}
            hint={`Connected ${when(c.created_at)} · last used ${when(c.last_used_at)}`}
            control={
              <Button size="sm" disabled={busy === c.id} onClick={() => void disconnect(c)}>
                {busy === c.id ? "Disconnecting…" : "Disconnect"}
              </Button>
            }
          />
        ))
      )}
    </SettingsCard>
  );
}

export function ConnectionsSection() {
  const { me, toast } = useShell();
  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />
      <SettingsCard title="Servers" description="paste the address into the app" pad>
        <ConnectMcpBody me={me} toast={toast} />
      </SettingsCard>
      <Apps />
    </>
  );
}
