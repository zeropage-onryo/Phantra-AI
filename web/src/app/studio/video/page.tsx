import { DirectGenerator } from "@/components/studio/direct-generator";

/* /studio/video (2026-10-22): pick a video model, type a prompt, see the
   price, press Generate -- from text alone or from one start frame. The
   other door beside Create's chat; see
   components/studio/direct-generator.tsx. */
export default function VideoPage() {
  return <DirectGenerator kind="video" />;
}
