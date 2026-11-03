import { Suspense } from "react";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { VoiceTab } from "@/components/studio/voice-tab";

/* The Voice section (2026-10-26, docs/tasks/task-voice-tab.md), behind the
   `voice_tab` capability, asked of the API on the SERVER exactly as the
   Effects tab asks for `effects_tab` (app/studio/effects/page.tsx): with the
   flag off -- or with no session -- this address is a plain 404. */

export const dynamic = "force-dynamic";

const UPSTREAM = () => (process.env.API_UPSTREAM || "http://localhost:8000").replace(/\/+$/, "");

async function voiceTabOn(): Promise<boolean> {
  try {
    const jar = await cookies();
    const cookie = jar
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join("; ");
    const res = await fetch(`${UPSTREAM()}/api/capabilities`, { cache: "no-store", headers: cookie ? { cookie } : {} });
    if (!res.ok) return false;
    const caps = (await res.json()) as { voice_tab?: unknown };
    return caps.voice_tab === true;
  } catch {
    return false;
  }
}

export default async function VoicePage() {
  if (!(await voiceTabOn())) notFound();
  // useSearchParams (the ?model= and ?on= hand-offs) needs a boundary
  return (
    <Suspense>
      <VoiceTab />
    </Suspense>
  );
}
