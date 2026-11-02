// The pure half of the referral cookie (no imports, so node --test can load it).
export const REF_COOKIE = "phantra_ref";
const CODE_RE = /^[a-z0-9][a-z0-9_-]{2,39}$/;

/** A ?ref= value as the server will read it, or null when it cannot be a code. */
export function cleanRef(raw: string | null | undefined): string | null {
  const code = (raw ?? "").trim().toLowerCase();
  return CODE_RE.test(code) ? code : null;
}

/** The Set-Cookie string for a visit to a partner's link. The domain is the
 *  apex so api.phantra.ai receives it at sign-in; anywhere else (local dev,
 *  a preview host) it stays host-only. */
export function refCookie(code: string, hostname: string, https: boolean, days = 60): string {
  const apex = hostname === "phantra.ai" || hostname.endsWith(".phantra.ai");
  return [
    `${REF_COOKIE}=${code}`,
    `Max-Age=${days * 86400}`,
    "Path=/",
    "SameSite=Lax",
    ...(apex ? ["Domain=.phantra.ai"] : []),
    ...(https ? ["Secure"] : []),
  ].join("; ");
}

export function readRef(cookie: string): string | null {
  const hit = cookie.split(/;\s*/).find((p) => p.startsWith(`${REF_COOKIE}=`));
  return hit ? cleanRef(decodeURIComponent(hit.slice(REF_COOKIE.length + 1))) : null;
}

export function dollars(cents: number): string {
  return `$${(cents / 100).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
