import { DirectGenerator } from "@/components/studio/direct-generator";

/* /studio/image (2026-10-22): pick an image model, type a prompt, see the
   price, press Generate. The other door beside Create's chat; see
   components/studio/direct-generator.tsx. */
export default function ImagePage() {
  return <DirectGenerator kind="image" />;
}
