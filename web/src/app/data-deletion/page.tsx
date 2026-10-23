import type { Metadata } from "next";
import Link from "next/link";
import { LEGAL_CONTACT, LegalPage, type LegalSection } from "@/components/legal-page";
import { pageMeta } from "@/lib/page-meta";

// The data deletion instructions page (2026-10-23). Meta's app registration
// requires a "Data deletion instructions URL" and TikTok's and Google's
// reviews read the same page; it is also the plain answer to "how do I get
// my data out of here". Each sentence was checked against the code that
// day: src/social_connections.remove (Disconnect wipes the token at once,
// the row stays as history), the Library's soft delete (src/render_assets),
// and the fact that there is no self-serve account deletion yet -- that is a
// mailed request, answered by hand, and this page says so rather than
// promising a button that does not exist.

export const metadata: Metadata = pageMeta({
  title: "Data Deletion",
  description: "How to remove your data from Phantra: disconnect an account, delete your work, or ask for the whole account to go.",
  path: "/data-deletion",
});

const SECTIONS: LegalSection[] = [
  {
    title: "Disconnect a social account",
    body: (
      <p>
        Go to Settings → Connections and press <strong>Disconnect</strong> beside the account.
        The access token the platform issued is wiped at that moment and the Studio can no longer
        post for that account or read its feed. The record that the account was once connected
        (its name and when) is kept so your history of posts still reads correctly; it goes with
        the rest of your data when the account is deleted. You can also revoke the Studio from the
        platform&apos;s own side (Instagram: Settings → Apps and websites; Discord: the
        server&apos;s Integrations; Reddit: Preferences → Apps; LinkedIn: Settings → Data privacy →
        Permitted services; TikTok: Settings → Security → Manage app permissions; YouTube: your
        Google Account → Third-party apps; X: Settings → Security → Apps and sessions). A token
        revoked there stops working at once and the Studio shows the connection as needing to be
        reconnected.
      </p>
    ),
  },
  {
    title: "Delete your work",
    body: (
      <p>
        A render deleted in the Library leaves it at once and sits in the trash for seven days,
        then its file is removed. Elements (characters, products, places) and their photos are
        deleted from their own pages. A scheduled post that has not gone out is cancelled from
        the calendar; a post that has already landed on a platform is removed there, on the
        platform, not from here.
      </p>
    ),
  },
  {
    title: "Delete your account",
    body: (
      <>
        <p>
          Email <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a> from the address on your
          account with the subject <em>Delete my account</em>. Within 30 days your account, your
          workspace, every connected-account record and token, your uploads, renders and cuts, and
          your billing history on our side are deleted. Stripe keeps the invoice records the law
          requires it to keep; platforms you posted to keep what you posted there.
        </p>
        <p>
          Removing Phantra from an Instagram or Facebook account under that account&apos;s Apps and
          websites settings revokes the token on Meta&apos;s side at once; the request above is
          what removes the record and everything else. It ends with a confirmation to your email.
        </p>
      </>
    ),
  },
  {
    title: "Questions",
    body: (
      <p>
        The <Link href="/privacy">privacy policy</Link> says what is collected and why; anything
        it does not answer can be asked at <a href={`mailto:${LEGAL_CONTACT}`}>{LEGAL_CONTACT}</a>.
      </p>
    ),
  },
];

export default function DataDeletionPage() {
  return (
    <LegalPage
      title="Data Deletion"
      dek="How to remove your data from Phantra: disconnect an account, delete your work, or ask for the whole account to go."
      effective="23 Oct 2026"
      sections={SECTIONS}
    />
  );
}
