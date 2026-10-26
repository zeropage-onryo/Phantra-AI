import type { Metadata } from "next";
import { ProfilePage } from "@/components/studio/phone/profile";

export const metadata: Metadata = { title: "Profile" };

/* /studio/me (2026-10-26): the phone's Profile tab, your credits and the
   account doors (components/studio/phone/profile.tsx). */
export default function Page() {
  return <ProfilePage />;
}
