# Publishing: drafted by Claude, sent by the person (2026-10-11)

Mike, 2026-10-10: make the studio a distribution platform as well, posting to
YouTube, Instagram, TikTok and LinkedIn. This is step one: one platform
(TikTok), built the way all four platforms' app reviews want it.

## What shipped

- **`src/publish_review.py`** introduces `publish_sessions`, an OWNED table holding one row per drafted post.
  - `prepare()` writes a draft and returns a review link. It sends nothing and spends nothing.
  - `review()` is what the page renders. While the post is a draft it fetches the account's `creator_info` fresh on every load.
  - `submit()` handles the press of Post:
    1. It re-reads `creator_info`.
    2. It validates every answer in `validate_tiktok`.
    3. It claims the row once, using `UPDATE … WHERE status = 'draft'`.
    4. It calls Direct Post init.
  - `refresh()` polls TikTok's status until the post is `published` or `failed`.
  - `cancel()` and `recent()` are also here.
- **`src/tiktok.py`** gains `creator_info()`, and `init_direct_post` / `post_video` take `options=` covering the rest of `post_info`:
  - `disable_comment`, `disable_duet` and `disable_stitch`
  - `brand_content_toggle` and `brand_organic_toggle`
  - `is_aigc` and the cover timestamp

  Unknown keys are dropped. Old callers are unchanged.
- **The MCP tool `prepare_post`** is on every unlisted surface. It returns a draft and `review_url`. No MCP tool can post: `tests/test_publish_review.py::test_no_mcp_path_reaches_submit` walks `mcp_server.py`'s AST for any call to `submit`, `init_direct_post`, `post_video` or `execute_post_action`.
- **`app/publish_routes.py`** adds `/api/publish`. Every route takes `current_account_id`:
  - `GET ""` lists recent posts.
  - `POST /prepare` drafts a post.
  - `GET /{id}` returns the review data.
  - `POST /{id}/submit` sends the post.
  - `POST /{id}/cancel` discards the draft.
- **`web/src/app/studio/publish/[id]/page.tsx`** is the review page.

## Why a page and not a quote token

The render tools approve spend with a signed quote and a yes in chat, and the price is the whole decision there. TikTok's Direct Post guidelines, which its audit checks, ask for much more:

- the poster sees a preview and the account name;
- picks privacy themselves, with no default;
- sets comments, Duet and Stitch, all unticked, and greyed out when off on the account;
- discloses commercial content ("Your brand" / "Branded content"; branded content cannot be "Only me");
- sees the declaration;
- consents before anything is sent.

A model saying yes on someone's behalf is exactly what those rules forbid. The page is also the screen recording the audit wants. Instagram, YouTube and LinkedIn reviews ask for the same shape.

## Decisions made here, for Mike to confirm

1. **Publishing stops being operator-only in shape, but not yet in credentials.**
   - `db.SHARED_TABLES` decided on 2026-09-02 that publishing stays the operator's.
   - `publish_sessions` is owned per account, because a draft is one account's.
   - The credential is still the env token, usable only by `PUBLISH_OPERATOR_ACCOUNT`.
   - Every other account sees "Connect your TikTok account first".
   - `publish_review.token_for` is the single seam per-account OAuth replaces.
2. **AI label.** Everything rendered by the studio (`gen:<id>`) is posted with `is_aigc=true`, locked on. Only an imported clip (`asset:<id>`) may turn the label off.
3. **Drafts expire after 24h.**

## The media host (TikTok domain verification)

TikTok pulls the file from the URL it is given and accepts only URLs on a domain or URL prefix verified on the developer app. A redirect is treated as invalid. Today clips live on Cloudflare's `pub-<hash>.r2.dev` host, which we cannot verify with DNS.

**Recommended fix: serve media from `media.phantra.ai`.**

1. Attach a custom domain to the R2 bucket. Cloudflare needs the `phantra.ai` zone on Cloudflare to do this; its DNS is on Vercel today. That move is Mike's call.
2. Verify `media.phantra.ai` (or `phantra.ai`, which covers subdomains) as a Domain property on the TikTok app, using a DNS TXT record.
3. Set the variables:
   - `TIKTOK_VERIFIED_URL_PREFIXES=media.phantra.ai`
   - `PUBLISH_MEDIA_BASE_URL=https://media.phantra.ai`

   Existing bucket URLs are rewritten onto that host with the same key.

Until then, `media_problem()` fails closed before the press with that instruction. The page shows it, and `prepare_post` returns it.

## Next

- **Per-account OAuth connections** for TikTok (Login Kit) through `token_for`. This is needed before any non-operator user can post, and before the audit.
- **Instagram Reels adapter.** `instagram.post_reel` already takes a token and a public URL. Needs Meta App Review plus Business Verification.
- **YouTube adapter.** `youtube.upload_video` uploads bytes, so no domain verification is needed. Needs the YouTube API compliance audit, because unaudited uploads are forced private.
- **LinkedIn adapter.** "Share on LinkedIn" (`w_member_social`) is self-serve. Company pages need the Community Management API.
- **TikTok Photo Mode** (one to ten images) and scheduling from the page.
- **Close the second TikTok door.** `tiktok.execute_post_action` (autopilot, scheduling, the holds' "Post now") still posts directly, with no creator_info, review page or consent; it defaults to SELF_ONLY and sits behind the L4 gate (off by default). Before the TikTok audit, either refuse `platform == "tiktok"` in `autopilot.execute` or route it through `publish_review.prepare`. That is Mike's call, since it changes the autopilot.
