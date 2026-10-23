// Phantra's own social accounts (Mike, 2026-10-23). The header's Resources
// menu, the phone menu and the home page's Organization JSON-LD (`sameAs`)
// all read this one list, so adding an account is one line here.
export type SocialIcon = "instagram" | "tiktok" | "x" | "linkedin" | "discord" | "youtube";

export type Social = {
  label: string;
  handle: string;
  href: string;
  icon: SocialIcon;
};

export const SOCIALS: Social[] = [
  { label: "Instagram", handle: "@phantra.ai", href: "https://www.instagram.com/phantra.ai/", icon: "instagram" },
  { label: "TikTok", handle: "@phantra.ai", href: "https://www.tiktok.com/@phantra.ai", icon: "tiktok" },
  { label: "X", handle: "@phantra_ai", href: "https://x.com/phantra_ai", icon: "x" },
  { label: "LinkedIn", handle: "Phantra AI", href: "https://www.linkedin.com/company/phantra-ai/", icon: "linkedin" },
  // the permanent invite (never expires), landing in #welcome (2026-10-23)
  { label: "Discord", handle: "Join the community", href: "https://discord.gg/tdwCwDJyH", icon: "discord" },
];
