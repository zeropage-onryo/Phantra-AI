import { PluginsReview } from "@/components/studio/plugins/variants";

/* /studio/plugins (2026-10-23): where the Plugins flyout's DaVinci Resolve
   and Premiere Pro rows open, inside the studio (#resolve, #premiere).
   Five layouts for Mike to pick from, ?v=1..5; the strip at the top is for
   that review and goes with the four not picked. */
export default async function PluginsPage({ searchParams }: { searchParams: Promise<{ v?: string }> }) {
  const { v } = await searchParams;
  return <PluginsReview key={v ?? "1"} v={v} />;
}
