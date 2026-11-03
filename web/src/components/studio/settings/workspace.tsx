"use client";

/* Settings → Workspace (2026-10-11): the workspaces the person belongs to,
   the switch between them, and who is in the one that is open.

   Since 2026-11-03 (the Agency plan) an OWNER on a plan with seats invites
   teammates by address here and removes them; nothing is emailed, the
   person signs in with that address. Below Agency there are no seats, and
   the card says where they come from. An owner sees addresses; a member
   sees names. The open workspace is the one work goes to. */
/* eslint-disable @next/next/no-img-element -- the provider's own avatar, already small */
import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { getMembers, inviteMember, removeMember, switchAccount, type Members } from "@/lib/studio-api";
import { SECTIONS } from "@/lib/settings-sections";
import { useShell } from "@/components/studio/shell";
import {
  Badge,
  Button,
  EmptyState,
  Field,
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
  const { me, refreshMe, toast } = useShell();
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
  const several = (me?.accounts.length ?? 0) > 1;
  const [email, setEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const reread = () => {
    if (account === null) return;
    getMembers().then(
      (data) => setRead({ account, data, error: null }),
      () => {},
    );
  };
  const invite = () => {
    const address = email.trim();
    if (!address || inviting) return;
    setInviting(true);
    inviteMember(address)
      .then((r) => {
        setEmail("");
        toast(
          r.joined_existing_user
            ? `${r.email} can open this workspace from their workspace switch now`
            : `${r.email} joins when they sign in at phantra.ai with that address`,
        );
        reread();
      })
      .catch((err) => toast(errorText(err, "Could not invite them"), "err"))
      .finally(() => setInviting(false));
  };
  const remove = (id: string, who: string) => {
    if (removing) return;
    setRemoving(id);
    removeMember(id)
      .then(() => {
        toast(`${who} was removed. What they made stays here.`);
        reread();
      })
      .catch((err) => toast(errorText(err, "Could not remove them"), "err"))
      .finally(() => setRemoving(null));
  };

  const go = (slug: string) => {
    setSwitching(slug);
    switchAccount(slug)
      .then(
        () =>
          // every page keys what it shows on the workspace the shell hands
          // out, so re-reading /api/me is the switch (as in the rail's menu).
          // The cookie is already set: if that read fails, a reload says it.
          refreshMe().then(
            () => setSwitching(null),
            () => window.location.reload(),
          ),
        () => {
          setSwitching(null);
          toast("Could not switch workspace", "err");
        },
      );
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
                <>You are {a.role === "owner" ? "an owner" : "a member"}.</>
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
        {several ? (
          <p className="zset-note zset-foot">
            Switching changes the workspace you work in: its credits, projects, scenes and elements.
          </p>
        ) : null}
      </SettingsCard>

      {active ? (
        <SettingsCard
          title={`Members of ${members?.data?.account.label ?? active.label}`}
          description={
            members?.data
              ? (members.data.seats ?? 1) > 1
                ? `${members.data.used ?? members.data.members.length} of ${members.data.seats} seats used`
                : `${members.data.members.length} in this workspace`
              : undefined
          }
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
                      {members.data!.role === "owner" && m.role !== "owner" && m.id ? (
                        <Button onClick={() => remove(m.id!, m.name)} disabled={removing !== null}>
                          {removing === m.id ? "Removing…" : "Remove"}
                        </Button>
                      ) : null}
                    </span>
                  </li>
                ))}
              </ul>
              {members.data.can_invite ? (
                <form
                  className="zset-card-pad zset-invite"
                  onSubmit={(e) => {
                    e.preventDefault();
                    invite();
                  }}
                >
                  <Field
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="teammate@agency.com"
                    aria-label="Teammate's email address"
                    disabled={inviting || (members.data.used ?? 0) >= (members.data.seats ?? 1)}
                  />
                  <Button
                    type="submit"
                    variant="primary"
                    disabled={inviting || !email.trim() || (members.data.used ?? 0) >= (members.data.seats ?? 1)}
                  >
                    {inviting ? "Inviting…" : "Invite"}
                  </Button>
                </form>
              ) : null}
              <p className="zset-note zset-foot">
                {members.data.can_see_emails
                  ? "As an owner you see everyone’s address. Members see names only."
                  : "Members see names only. Owners see addresses."}{" "}
                {members.data.can_invite
                  ? (members.data.used ?? 0) >= (members.data.seats ?? 1)
                    ? "Every seat is taken. Remove someone to invite another person."
                    : "Nothing is emailed: they join when they sign in at phantra.ai with that address, and share this workspace’s credits."
                  : members.data.role === "owner"
                    ? "Inviting teammates comes with the Agency plan: five seats on one credit pool."
                    : "People are invited by the workspace’s owner."}
              </p>
            </>
          )}
        </SettingsCard>
      ) : null}
    </>
  );
}
