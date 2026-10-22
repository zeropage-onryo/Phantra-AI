import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { EffectsTab } from "@/components/studio/effects-tab";

/* The Effects tab (2026-10-22, docs/tasks/task-effects-tab.md), behind the
   `effects_tab` capability. The flag is asked of the API on the SERVER,
   per request (the same upstream the rewrites proxy to), with the
   person's own cookies forwarded: /api/capabilities sits behind the
   session like every /api route, and the session cookie lives on THIS
   origin (the sign-in handoff puts it here), so it rides along as it
   does through the proxy. With the flag off -- or with no session, which
   is the same answer -- this address is a plain 404, not a page that
   redirects after it has drawn, so a curl shows the posture and
   production is unchanged. */

export const dynamic = "force-dynamic";

const UPSTREAM = () => (process.env.API_UPSTREAM || "http://localhost:8000").replace(/\/+$/, "");

async function effectsTabOn(): Promise<boolean> {
  try {
    const jar = await cookies();
    const cookie = jar
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join("; ");
    const res = await fetch(`${UPSTREAM()}/api/capabilities`, { cache: "no-store", headers: cookie ? { cookie } : {} });
    if (!res.ok) return false;
    const caps = (await res.json()) as { effects_tab?: unknown };
    return caps.effects_tab === true;
  } catch {
    return false;
  }
}

export default async function EffectsPage() {
  if (!(await effectsTabOn())) notFound();
  return <EffectsTab />;
}
