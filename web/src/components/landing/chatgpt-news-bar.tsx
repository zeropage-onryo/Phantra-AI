import { BrandLogo } from "@/components/mcp/brand-logos";
import { CHATGPT_PLUGIN_URL } from "@/lib/connect-claude";

// The news bar on the homepage hero (2026-11-02, Mike: "have NOW IN CHATGPT
// be like its a news or banner", the 17d pick): one lemon strip under the
// header saying Phantra is an approved ChatGPT app, the whole strip a link to
// the plugin's page in ChatGPT's directory. The OpenAI mark only names where
// it opens; nothing here says OpenAI endorses Phantra.
export function ChatGptNewsBar() {
  return (
    <a
      href={CHATGPT_PLUGIN_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="group relative z-20 flex min-h-[52px] items-center justify-center gap-3 bg-[var(--lemon)] px-4 py-2 text-[var(--lemon-ink)] sm:gap-4 lg:min-h-[60px]"
    >
      <span
        aria-hidden
        className="hidden size-8 flex-none items-center justify-center rounded-full bg-[var(--lemon-ink)] text-white sm:inline-flex lg:size-9"
      >
        <BrandLogo name="openai" className="size-[18px] lg:size-5" />
      </span>
      <span className="text-[15px] font-bold tracking-[-0.01em] lg:text-[19px]">
        Phantra is now an approved ChatGPT app.
      </span>
      <span className="hidden text-[16px] xl:inline lg:text-[17px]">Make images and video without leaving your chat.</span>
      <span className="inline-flex flex-none items-center gap-2 rounded-full bg-[var(--lemon-ink)] px-3.5 py-2 text-[14px] font-bold text-white transition-colors group-hover:bg-[#252422] lg:text-[15px]">
        <BrandLogo name="openai" className="size-4 lg:size-[18px]" />
        <span className="hidden sm:inline">Open in ChatGPT</span>
        <span className="sm:hidden">Open</span>
        <span aria-hidden>→</span>
        <span className="sr-only">(opens in a new tab)</span>
      </span>
    </a>
  );
}
