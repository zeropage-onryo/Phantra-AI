"use client";

/* Settings → Workspace (2026-10-11): the workspaces the person belongs to,
   the switch between them, and who is in the one that is open.

   The members list is read only. Membership is granted by members, never
   by signing up and never from a page: an invite form is its own decision
   (docs/BACKLOG.md #22), so this says how people are added and adds
   nobody. An owner sees addresses; a member sees names. */
/* eslint-disable @next/next/no-img-element -- the provider's own avatar, already small */
import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { getMembers, switchAccount, type Members } from "@/lib/studio-api";
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import {
  Badge,
  Button,
  EmptyState,
  Notice,
  Row,
  SectionHeader,
  SettingsCard,
  SkeletonRows,
  errorText,
} from "@/components/studio/settings/ui";

const SECTION = SECTIONS.find((s) => s.id === "workspace")!;

const initialOf = (name: string) => (name.trim()[0] || "?").toUpperCase();
const roleWord = (role: string) => (role === "owner" ? "Owner" : "Member");

export function WorkspaceSection() {
  const { me, toast } = useShell();
  const active = me?.account ?? null;
  const [switching, setSwitching] = useState<string | null>(null);
  // keyed by the workspace it was read for, so a switch never shows the
  // last one's people under the new one's name
  const [read, setRead] = useState<{ account: number; data: Members | null; error: string | null } | null>(null);

  const account = active?.id ?? null;
  useEffect(() => {
    if (account === null) return;
    let gone = false;
    getMembers()
      .then((data) => !gone && setRead({ account, data, error: null }))
      .catch((err) => !gone && setRead({ account, data: null, error: errorText(err, "Could not read the members") }));
    return () => {
      gone = true;
    };
  }, [account]);
  const members = read && read.account === account ? read : null;
  // somebody in more than one workspace is told where their work lives:
  // the studio keeps it in the FIRST one they joined, whichever is open
  const home = members?.data?.home ?? null;
  const several = (me?.accounts.length ?? 0) > 1;

  const go = (slug: string) => {
    setSwitching(slug);
    switchAccount(slug)
      // a full reload: every page keys what it shows on the workspace
      .then(() => window.location.reload())
      .catch(() => {
        setSwitching(null);
        toast("Could not switch workspace", "err");
      });
  };

  return (
    <>
      <SectionHeader title={SECTION.label} description={SECTION.description} />

      <SettingsCard title="Your workspaces">
        {!me ? (
          <SkeletonRows rows={2} />
        ) : me.accounts.length === 0 ? (
          <EmptyState icon={Users} title="No workspace yet">
            People are added to a workspace by someone already in it, never by signing up. Ask the person who runs
            yours to add this address.
          </EmptyState>
        ) : (
          me.accounts.map((a) => (
            <Row
              key={a.id}
              label={
                <span className="zset-ws">
                  <span className="zset-ws-dot" style={a.accent ? { background: a.accent } : undefined} aria-hidden />
                  {a.label}
                  {a.id === active?.id ? <Badge tone="ok">Active</Badge> : null}
                </span>
              }
              hint={
                <>
                  You are {a.role === "owner" ? "an owner" : "a member"}.
                  {several && home?.id === a.id ? " Your credits, scenes and elements live here." : ""}
                </>
              }
              control={
                a.id === active?.id ? null : (
                  <Button onClick={() => go(a.slug)} disabled={switching !== null}>
                    {switching === a.slug ? "Switching…" : "Switch"}
                  </Button>
                )
              }
            />
          ))
        )}
        {several && home ? (
          <p className="zset-note zset-foot">
            Switching changes which workspace the studio shows. Your credits, scenes and elements stay in{" "}
            <b>{home.label}</b>, the first workspace you joined.
          </p>
        ) : null}
      </SettingsCard>

      {active ? (
        <SettingsCard
          title={`Members of ${members?.data?.account.label ?? active.label}`}
          description={members?.data ? `${members.data.members.length} in this workspace` : undefined}
        >
          {members?.error ? (
            <div className="zset-card-pad">
              <Notice tone="err">{members.error}</Notice>
            </div>
          ) : !members?.data ? (
            <SkeletonRows rows={3} />
          ) : (
            <>
              <ul className="zset-members">
                {members.data.members.map((m, i) => (
                  <li key={`${m.name}-${m.email ?? i}`}>
                    <span className="zset-member-face" aria-hidden>
                      {m.avatar_url ? <img src={m.avatar_url} alt="" /> : initialOf(m.name)}
                    </span>
                    <span className="zset-member-who">
                      <b>
                        {m.name}
                        {m.you ? <Badge>You</Badge> : null}
                      </b>
                      {m.email ? <span>{m.email}</span> : null}
                    </span>
                    <span className="zset-member-tags">
                      {!m.claimed ? <Badge tone="warn">Invited</Badge> : null}
                      <Badge tone={m.role === "owner" ? "signal" : undefined}>{roleWord(m.role)}</Badge>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="zset-note zset-foot">
                {members.data.can_see_emails
                  ? "As an owner you see everyone’s address. Members see names only."
                  : "Members see names only. Owners see addresses."}{" "}
                People are added by invitation, by someone who runs the workspace. There is no invite form here yet.
              </p>
            </>
          )}
        </SettingsCard>
      ) : null}
    </>
  );
}
