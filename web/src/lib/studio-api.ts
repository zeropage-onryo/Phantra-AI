/* The studio surfaces' calls into FastAPI, typed against what app/api.py
   returns today. Everything goes through the same-origin proxy
   (next.config.ts rewrites /api, /ui, /account, the photo routes) so the
   phantra_session cookie rides along untouched. Nothing here spends: the
   billed routes (scenes/run, the exec/* nodes) are the same gated ones
   the Jinja shell calls, and Send to Queue only PICKS. */
import { API_URL, ApiError, apiFetch } from "@/lib/api";
import type { AssistantDirection, AssistantQuestion, ContactSheet } from "@/lib/assistant";
import type { Skill } from "@/lib/skills";
import type { Effect, OptionValue } from "@/lib/effects";
import type { TalkMenu } from "@/lib/talking-photo";
import type { RoleOption } from "@/lib/ref-roles";
import type { LookResearch } from "@/lib/look-research";
import type { History as CreditHistory } from "@/lib/credit-history";
import type { Kit, KitSpec } from "@/lib/brand-kit";

export { ApiError };

/* ── who ── */
export type Account = {
  id: number;
  slug: string;
  label: string;
  accent?: string | null;
  role?: string | null;
};
export type Me = {
  user: {
    id: string;
    email: string | null;
    display_name: string;
    avatar_url: string | null;
  };
  account: Account | null;
  accounts: Account[];
  /** the address to paste into claude.ai (app/mcp_auth.connector_url);
   *  null when this server takes no person's connection, absent on an
   *  older API */
  mcp_url?: string | null;
  /** the connector's Claude directory listing, once it has one */
  claude_directory_url?: string | null;
};
export const getMe = () => apiFetch<Me>("/me");

/* who is in the workspace that is open (Settings → Workspace, 2026-10-11).
   Read only. An owner is sent every address; a member is sent names, and
   no address but their own (app/api.py account_members). */
export type Member = {
  name: string;
  email: string | null;
  avatar_url: string | null;
  role: string;
  /** false: invited, and has not signed in yet */
  claimed: boolean;
  you: boolean;
};
export type Members = {
  account: { id: number; slug: string; label: string };
  role: string;
  can_see_emails: boolean;
  members: Member[];
  /** the workspace the studio's data routes act on: the caller's FIRST
   *  one, whichever is open (app/auth.py current_account_id) */
  home?: { id: number; slug: string; label: string } | null;
};
export const getMembers = () => apiFetch<Members>("/account/members");

/* whether THIS person has connected Claude to this account
   (src/mcp_connections.py): recorded when they press Allow on the consent
   page, stamped when Claude uses it. claude.ai is never asked. */
export type McpConnection = {
  connected: boolean;
  approved_at: string | null;
  last_used_at: string | null;
  client_name: string | null;
};
export const getMcpConnection = () => apiFetch<McpConnection>("/mcp/connection");

/* ── settings (2026-10-03): the person's own row and their password ──
   PATCH /api/me renames; the password and email writes each re-prove the
   person (their current password, or a code mailed by sendSecurityCode)
   and the API mints a one-call Supabase session for the write -- nothing
   of Supabase's is kept, and nothing here spends. */
export const updateMe = (display_name: string) =>
  apiFetch<Me>("/me", { method: "PATCH", body: JSON.stringify({ display_name }) });
export type Security = {
  email: string | null;
  /** what the API KNOWS: false also for a password set before it kept track */
  has_password: boolean;
  password_set_at: string | null;
  /** Supabase is wired, so a password or email change can be made */
  can_change: boolean;
  min_password_len: number;
};
export const getSecurity = () => apiFetch<Security>("/me/security");
export const sendSecurityCode = () =>
  apiFetch<{ sent: boolean; email: string }>("/me/security/code", { method: "POST" });
export type Proof = { current_password?: string; code?: string };
export const setPassword = (password: string, password2: string, proof: Proof) =>
  apiFetch<{ ok: boolean } & Security>("/me/password", {
    method: "POST",
    body: JSON.stringify({ password, password2, ...proof }),
  });
export const changeEmail = (email: string, proof: Proof) =>
  apiFetch<{ ok: boolean; pending: string; note: string }>("/me/email", {
    method: "POST",
    body: JSON.stringify({ email, ...proof }),
  });

/* ── what may be drawn ── */
export type Capabilities = Record<string, boolean>;
export const getCapabilities = () => apiFetch<Capabilities>("/capabilities");

/* ── assets (elements) ── */
export type AssetCategory = "character" | "location" | "prop";
export type Asset = {
  id: string;
  /** the studio's own rendered stills come back as "generated" beside the
   *  three element kinds (app/api.py _assets_all) */
  category: AssetCategory | "generated";
  name: string;
  /** stored NAMES, what a shot keeps -- never an address to draw from
   *  (lib/element-photos.ts) */
  photos: string[];
  /** where each photo is, parallel to `photos`, minted for this account:
   *  the full-size master and the 480px derivative (elements only) */
  photo_full?: string[];
  photo_thumbs?: string[];
  poster: string | null;
  /** the drawn reference sheet, when one exists — FIRST in `photos`, and what the element is used as (2026-10-12) */
  sheet?: string | null;
  text: string;
  meta: Record<string, unknown>;
  created_at?: string | null;
  /** how many open concepts' refs name this element (scope=elements only,
   *  counted server-side through asset_shelf.parse_ref, 2026-09-25) */
  used_in?: number;
};
/* Which half of the bank (2026-09-18): `elements` is the characters /
   locations / props a shot is held to, `generated` is the renders, `all`
   is both -- the server's default, kept for the one caller that needs a
   generated id to resolve (the composer's ?attach= handoff). */
export type AssetScope = "all" | "elements" | "generated";
/* Elements deleted on a page whose DELETE is held behind the toast's Undo
   (element-sheet.tsx useElementDelete, 2026-10-08): the server still has
   them until the toast closes, so every listing read in that window leaves
   them out here, in the one place the pages read elements from. */
const heldDeletes = new Set<string>();
export const holdElementDelete = (id: string, held: boolean) => {
  if (held) heldDeletes.add(id);
  else heldDeletes.delete(id);
};
export const getAssets = (q?: string, scope: AssetScope = "elements") => {
  const params = new URLSearchParams({ scope });
  if (q) params.set("q", q);
  return apiFetch<{ items: Asset[] }>(`/assets?${params}`).then((r) =>
    heldDeletes.size ? { ...r, items: r.items.filter((a) => !heldDeletes.has(a.id)) } : r,
  );
};

/* GET /api/search (src/search.py, 2026-10-08): the ⌘K palette's one
   question across everything this account made. An empty q is the recent
   list (projects and open scenes). `thumb` is drawable as it comes. */
export type SearchProject = { id: number; title: string; sub: string; archived: boolean; thumb: string | null };
export type SearchScene = {
  id: number;
  n: string;
  title: string;
  sub: string;
  project_id: number | null;
  project_title: string | null;
  picked: boolean;
  archived: boolean;
  rendered: boolean;
  thumb: string | null;
};
export type SearchElement = {
  id: string;
  kind: "character" | "prop" | "product" | "place";
  name: string;
  sub: string;
  frames: number;
  thumb: string | null;
};
export type SearchRender = { id: number; kind: "image" | "video"; label: string; sub: string; concept_id: number | null; thumb: string | null };
export type SearchCut = { id: string; title: string; concept_id: number | null };
export type SearchResult = {
  q: string;
  recent: boolean;
  groups: {
    projects: SearchProject[];
    scenes: SearchScene[];
    elements: SearchElement[];
    renders: SearchRender[];
    cuts: SearchCut[];
  };
};
export const globalSearch = (q: string, init?: RequestInit) =>
  apiFetch<SearchResult>(`/search?q=${encodeURIComponent(q)}`, init);

export type AssetHit = { name: string; category: AssetCategory; thumb: string | null };
export const searchAssets = (q: string) =>
  apiFetch<{ items: AssetHit[] }>(`/assets/search?q=${encodeURIComponent(q)}`);

/* Routes behind app/model_connections.mutation_header refuse any request
   that does not carry this header (403, before any work). It exists so a
   SameSite=None studio session cannot be spent by a cross-site form post:
   a custom header forces a CORS preflight. Send it from ONE place -- the
   Jinja client sends it per call site and the React composer was ported
   without it, which 403'd every Guide turn silently (2026-09-14). */
export const GUARDED_HEADERS: Record<string, string> = {
  "X-Phantra-Model-Connection": "1",
};

/* multipart: apiFetch pins a JSON content-type, so uploads go direct */
async function apiForm<T>(
  path: string,
  form: FormData,
  headers?: Record<string, string>,
): Promise<T> {
  const res = await fetch(`${API_URL}/api${path}`, {
    method: "POST",
    credentials: "include",
    ...(headers ? { headers } : {}),
    body: form,
  });
  if (!res.ok) {
    let message = res.statusText || `request failed (${res.status})`;
    let code: string | undefined;
    try {
      const body = await res.clone().json();
      message = body?.error?.message ?? body?.detail ?? message;
      code = body?.error?.code;
    } catch {
      /* not JSON */
    }
    throw new ApiError(message, res.status, code);
  }
  return (await res.json()) as T;
}

export type AssetCreated = {
  ok: boolean;
  slug: string;
  photos: number;
  described?: boolean;
  note?: string | null;
  /** the job drawing the element's reference sheet, when one was asked for (2026-09-18) */
  sheet_job?: number | null;
  /** why no sheet was started when one was asked for (no key, no photos) */
  sheet_note?: string | null;
};
export type ElementKind = "characters" | "locations" | "props";
/** POST /api/assets/{kind}/{id}/sheet — draw (or redraw) an element's
 *  reference sheet from its real photos; cents on Nano Banana Pro. */
export const drawSheet = (kind: ElementKind, id: number) =>
  apiFetch<{ job_id: number }>(`/assets/${kind}/${id}/sheet`, { method: "POST", body: "{}" });
/** POST /api/assets/{characters|locations|props} — the always-on create
 *  path; every save also teaches the RAG assets shelf. */
export const createAsset = (
  kind: "characters" | "locations" | "props",
  form: FormData,
) => apiForm<AssetCreated>(`/assets/${kind}`, form);

/* ── the media wall ── */
export type MediaItem = {
  url: string;
  asset_id: string;
  asset_name: string;
  category: AssetCategory | "generated";
  kind: "image" | "video";
  date: string;
  /* generated rows only (2026-09-18) */
  generated_id?: number;
  provider?: string | null;
  model?: string | null;
  /** the model's public name ("FLUX.2 Pro", "Kling 3 Turbo Pro"), or null
   *  when no table knows the id (2026-10-20) */
  model_label?: string | null;
  /** this clip is a cheap draft of its shot (src/drafts.py): the frame it
   *  was rendered at. Finishing it is the Renders page's "Ready to cut" button. */
  draft?: { frame: string; model: string } | null;
  concept_id?: number | null;
  shot_n?: number | null;
  prompt?: string;
  folder?: string | null;
  starred?: boolean;
  /* a clip's still (2026-09-28): its t/ derivative, when R2 has one */
  poster?: string | null;
  /* a still's 480px thumbnail for the wall's tiles (2026-10-19), when R2
     has one; the viewer always draws `url`, the master */
  thumb?: string | null;
  /* when the render was made (2026-10-19), for the viewer's Created row */
  created_at?: string | null;
  /* the project its scene is filed under, or null: a render made outside
     any project lives here and on no board (2026-10-07) */
  project_id?: number | null;
  project_title?: string | null;
};
export type MediaCounts = Record<string, number> & { all: number };
export type MediaWall = {
  items: MediaItem[];
  counts: MediaCounts;
  wall: { image: number; video: number; starred: number };
  folders: Record<string, number>;
  providers: Record<string, number>;
};
export type MediaFilter = {
  q?: string;
  kind?: "image" | "video";
  folder?: string;
  starred?: boolean;
  provider?: string;
};
/** GET /api/media?kind=all&scope=generated — one row per render, newest
 *  first; `counts`/`wall`/`folders`/`providers` are set totals, never
 *  page length. The Assets wall is generated content only (2026-09-18). */
export const getMedia = (f: MediaFilter = {}) => {
  const params = new URLSearchParams({ kind: f.kind ?? "all", scope: "generated" });
  if (f.q) params.set("q", f.q);
  if (f.folder) params.set("folder", f.folder);
  if (f.starred) params.set("starred", "true");
  if (f.provider) params.set("provider", f.provider);
  return apiFetch<MediaWall>(`/media?${params}`);
};
/** DELETE /api/assets/{characters|props|locations}/{id} — an element. */
export const deleteAsset = (kind: "characters" | "props" | "locations", id: number, init?: RequestInit) =>
  apiFetch<{ deleted: number }>(`/assets/${kind}/${id}`, { ...init, method: "DELETE" });
/** DELETE /api/assets/generated/{id} — into the TRASH: off the wall and
 *  the RAG shelf; restorable for the trash's days, then the file goes. */
export const deleteGenerated = (id: number) =>
  apiFetch<{ deleted: number }>(`/assets/generated/${id}`, { method: "DELETE" });
/** The trash (2026-10-20, src/storage_quota.py): renders deleted in the
 *  last `trash_days` days, newest first. */
export type TrashItem = {
  generated_id: number;
  kind: "image" | "video";
  url: string;
  poster: string | null;
  provider: string;
  prompt: string | null;
  deleted_at: string;
  purge_at: string | null;
};
export const getTrash = () => apiFetch<{ items: TrashItem[]; trash_days: number }>(`/assets/generated/trash`);
/** DELETE /api/assets/generated/{id}/forever — empty one render out of the
 *  trash now. 409 `in_use` when a scene or a cut still plays it. */
export const deleteForever = (id: number) =>
  apiFetch<{ purged: number }>(`/assets/generated/${id}/forever`, { method: "DELETE" });
/** GET /api/storage — the bar in Settings -> Plan. Bytes are decimal
 *  (1 GB = 10^9), the unit the plans are sold in; `measured` false means
 *  this server cannot count (no bucket), and nothing is refused then. */
export type StorageUsage = {
  measured: boolean;
  used_bytes: number | null;
  limit_bytes: number | null;
  trash_bytes: number | null;
  trash_count: number;
  trash_days: number;
  near: boolean;
  over: boolean;
  used_gb: string;
  limit_gb: string | null;
};
export const getStorage = () => apiFetch<StorageUsage>(`/storage`);
/** POST /api/assets/generated/{id}/restore — the Undo on deleteGenerated:
 *  back on the wall and the shelf. 404 when it was not removed. */
export const restoreGenerated = (id: number) =>
  apiFetch<{ restored: number }>(`/assets/generated/${id}/restore`, { method: "POST", body: "{}" });
/** PATCH /api/assets/generated/{id} — folder and/or star. A field left
 *  out is left alone; folder "" clears it. */
export const organizeGenerated = (id: number, body: { folder?: string; starred?: boolean }) =>
  apiFetch<{ id: number; folder: string | null; starred: boolean }>(`/assets/generated/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });

/** A render's public page (src/shares.py, 2026-10-20): nothing is public
 *  until Share is pressed on that item; Unshare takes the page down, and a
 *  later Share makes a new address. `path` is "/v/<token>" on this site. */
export type ShareState = { shared: boolean; token: string | null; path: string | null };
export const getShare = (id: number) => apiFetch<ShareState>(`/assets/generated/${id}/share`);
export const shareRender = (id: number) =>
  apiFetch<ShareState>(`/assets/generated/${id}/share`, { method: "POST", body: "{}" });
export const unshareRender = (id: number) =>
  apiFetch<ShareState>(`/assets/generated/${id}/share`, { method: "DELETE" });
/** GET /api/assets/generated/{id} — one render on the wall, for a page
 *  handed only its id (the composer's `?on=`): what it is, a tile, and the
 *  `ref` an effect names it by. 404 for a removed one or another account's. */
export type RenderInfo = {
  id: number;
  ref: string;
  kind: "image" | "video";
  url: string;
  thumb: string | null;
  label: string;
  prompt: string;
};
export const getRender = (id: number) => apiFetch<RenderInfo>(`/assets/generated/${id}`);
/** GET /api/assets/generated/{id}/download — a link that SAVES the file:
 *  the server answers with a redirect to the bucket asking for an
 *  attachment (or serves its own copy). An href, never a fetch. */
export const renderDownloadHref = (id: number) => `${API_URL}/api/assets/generated/${id}/download`;

/** GET /api/ref-roles — what an attached reference can be FOR
 *  (src/ref_roles.py): the menu on each reference in the box. */
export const getRefRoles = () => apiFetch<{ roles: RoleOption[] }>("/ref-roles");

/* ── the board and the queue ── */
/** `up_to`: the count and the credits are the MOST a draw makes and charges
 *  (a scene with no timed shots, drawn as a still per moment of its move);
 *  absent, they are what it makes. The draw is capped at `stills` either way. */
export type KeyframeQuote = { stills: number; each: number; credits: number; part?: number; up_to?: boolean };
export type Concept = {
  id: number;
  n: string;
  title: string;
  summary: string;
  logline: string;
  spark: string | null;
  status: "idea" | "planned" | "shot";
  is_scene: boolean;
  picked: boolean;
  parked: boolean;
  archived: boolean;
  /** the studio project this scene is filed under, or null (a solo scene) */
  project_id?: number | null;
  park_reason: string;
  refs: string[];
  prompt: string;
  media_url: string;
  reference_image: string;
  created_at?: string;
  /** the card's own default renderer, resolved server-side from the shot's planned tool */
  render_default?: { provider: string; model: string };
  /** the clip model the brain proposed for this scene, and why (src/model_menu.py):
   *  render_default opens on it when the catalogue has it */
  render_model?: string;
  render_model_why?: string;
  /** pricing.display for the card's default pick (GET /api/scenes/{id}/render) */
  quote?: RenderQuote;
  /* the rest of app/api.py's _concept_card, read by the image-first cards */
  hook?: string | null;
  card_line?: string;
  warnings?: string[];
  graded?: boolean;
  shot_done?: boolean;
  subscription?: boolean;
  tool?: string;
  /** the Render card and Renders: why the reference gate refuses this
   *  scene ("" when it can be rendered). Shown, never approvable. */
  blocked?: string;
  /** where each reference came from, parallel to `refs` (app/api.py _ref_sources) */
  ref_sources?: import("./refs").RefSource[];
  /** the drawable size of each reference, parallel to `refs` (app/api.py
   *  _ref_thumbs, BACKLOG #0). `refs` stays the master: refs[0] anchors the render. */
  ref_thumbs?: string[];
  /** the timed shots a scene renders as, or null for one that renders whole */
  timeline?: Timeline | null;
  /** what drawing this scene's keyframes would cost; null when nothing to draw (2026-09-29) */
  keyframes?: KeyframeQuote | null;
};
export type TimelinePart = {
  n: number;
  start: number;
  end: number;
  seconds: number;
  text?: string | null;
  prompt?: string | null;
  refs?: string[] | null;
  /** parallel to `refs`, the card rule (app/api.py _ref_thumbs) */
  ref_thumbs?: string[] | null;
  reference_image?: string | null;
  media_url?: string | null;
};
export type Timeline = { planned: boolean; seconds?: number | null; parts: TimelinePart[] };
export type RendererModel = { id: string; label: string; usd_per_second: number };
/* the overnight branch's renderer catalogue (providers.render_options):
   every registered renderer with its gates, its models and each model's
   legal duration and frame axis; a price shape the card may multiply */
export type Axis = {
  kind: "choices" | "range" | "fixed";
  values?: (string | number)[];
  min?: number;
  max?: number;
  default?: string | number | null;
  note?: string;
};
export type ModelSpec = {
  id: string;
  label: string;
  available?: boolean;
  duration: Axis;
  frame: Axis;
  verified?: string | null;
  price?: { kind: "per_second" | "flat" | "unknown"; usd?: number; usd_by_frame?: Record<string, number> };
  /** the frame a draft renders at (src/drafts.py), or null: none offered */
  draft?: string | null;
};
export type RendererSpec = {
  label: string;
  available: boolean;
  spend_ok: boolean;
  spend_env?: string | null;
  cap?: number | null;
  today?: number | null;
  frame_axis: "ratio" | "resolution";
  models: ModelSpec[];
  default_model: string | null;
};
/** The default video renderer's state (app/api.py `_render_state`): fal.ai
 *  since 2026-09-26, the only video renderer. What the chips and older
 *  cards read; `renderers` is the full catalogue. */
export type RendererState = {
  label: string;
  provider: string;
  available: boolean;
  spend_ok: boolean;
  model: string;
  /** the provider's cost -- for the operator's own pages, never shown in the studio */
  estimate_usd: number;
  /** what the default clip costs in credits (pricing.credits_for), the
   *  number every studio surface shows; null when the server could not price it */
  credits?: number | null;
  duration?: number;
  resolution?: string;
  models?: RendererModel[];
  durations?: number[];
  today?: number | null;
};
/** src/pricing.py `display()` — the priced plan for one approve, or for
 *  the Director's Generate node: every render it would make, at what
 *  length, the provider's estimate and the credits it holds (every video
 *  render holds credits since 2026-09-26). `{error}` when the intent has no
 *  price. The server is the only place a price is computed. */
export type RenderQuote = {
  error?: string;
  provider: string;
  model: string;
  frame: string;
  timed: boolean;
  durations: number[];
  estimate_usd: number;
  credits: number | null;
  content_hash: string;
  /** tokens ride only when there is something to charge and QUOTE_SIGNING_SECRET is set */
  signed: boolean;
  renders: { part: number | null; seconds: number; estimate_usd: number; credits: number | null; token: string | null }[];
};
/** what approve takes: providers.check_render_choice refuses, never clamps */
export type RenderChoice = { provider?: string; model?: string; duration?: number; frame?: string; tokens?: string[] };
export type RenderResolved = { provider: string; model: string; duration: number; frame: string; estimate_usd: number };
export type PickRate = { generated: number; picked: number; rate: number | null };
/** The board's count line, counted on the server over the same window:
 *  scenes only; `picked` is open-and-picked (the Picked filter). */
export type BoardCounts = { open: number; picked: number; archived: number };
/** GET /api/pipeline/concepts — the board. `open` (the default) is the
 *  open cards; `archived` is the archived half of the same window, asked
 *  for only when the Archived filter is opened (2026-09-25). Either way
 *  `counts` says where every card went (the 2026-09-02 lesson) without
 *  the archived cards being fetched to count them. */
export const boardConcepts = (
  shelf: "open" | "archived" | "all" = "open",
  project?: number,
) => {
  const params = new URLSearchParams();
  if (shelf === "archived") params.set("view", "archived");
  // "all" is both halves of the window in one read -- a project's page
  // lists every scene it holds, passed ones included (2026-09-28)
  if (shelf === "all") params.set("archived", "true");
  if (project) params.set("project", String(project));
  const qs = params.toString();
  return apiFetch<{ items: Concept[]; counts: BoardCounts; pick?: PickRate }>(
    `/pipeline/concepts${qs ? `?${qs}` : ""}`,
  );
};
/** GET /api/pipeline/arrival — the ONE scene the Director opens on, or
 *  null. The rule (app/api.py `_arrival`) lives on the server so the page
 *  asks for an id, not the whole board (2026-09-25). */
export const directorArrival = () => apiFetch<{ id: number | null }>("/pipeline/arrival");
/** A line in the Director's scene switcher: the openable board rows only
 *  (`?view=menu`), no card, gates or sources. */
export type SceneMenuRow = {
  id: number;
  n: string;
  title: string | null;
  picked: boolean;
  parked: boolean;
  has_media: boolean;
};
export const sceneMenu = () =>
  apiFetch<{ items: SceneMenuRow[] }>("/pipeline/concepts?view=menu");
/** Remove a scene from its list, or put it back. A plain hide, never a
 *  delete: the row and anything rendered from it stay (2026-10-11 -- it
 *  used to be a verdict on the scene's writing as well). */
export const archiveConcept = (id: number, archived = true) =>
  apiFetch<{ ok: boolean }>(`/concepts/${id}/archive`, {
    method: "POST",
    body: JSON.stringify({ archived }),
  });
export const updateShotPrompt = (id: number, n: number, prompt: string) =>
  apiFetch<{ ok: boolean; warnings?: string[] }>(`/concepts/${id}/shots/${n}/prompt`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
/* THE SPEND IS ON THE SCENE (2026-10-11, docs/tasks/task-higgsfield-shape.md):
   a scene is rendered from its own Render card -- no board to pick it on
   first, no Queue page to approve it from. Three calls, one card
   (components/studio/render-card.tsx). */
/** GET /api/scenes/{id}/render — everything the Render card draws: the
 *  scene (its shots, stills and clips, `keyframes` still to draw, `blocked`
 *  when the reference gate refuses it, `render_default`, and `quote` for
 *  that default pick with its signed tokens) and the renderer catalogue.
 *  Spends nothing. */
export type SceneRender = { scene: Concept; renderer: RendererState; renderers: Record<string, RendererSpec> };
export const sceneRender = (id: number) => apiFetch<SceneRender>(`/scenes/${id}/render`);
/** what rendering WITH THIS PICK would make and cost — the server's own
 *  price; spends nothing. Asked when a pick differs from the one the card
 *  was served with. */
export const sceneQuote = (id: number, choice: RenderChoice) => {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(choice)) if (v !== undefined && v !== null) q.set(k, String(v));
  return apiFetch<RenderQuote>(`/scenes/${id}/quote?${q}`);
};
/** THE CLICK THAT SPENDS: render this scene with this pick and the signed
 *  quotes for it. Credit is held before anything is submitted. */
export const sceneApprove = (id: number, choice?: RenderChoice) =>
  apiFetch<{ job_id?: number; render?: RenderResolved; quote?: RenderQuote | null }>(`/scenes/${id}/approve`, {
    method: "POST",
    body: JSON.stringify(choice ?? {}),
  });
/** GET /api/renders/unfinished — scenes a render was started on that have
 *  no clip yet, read off the rows (so it survives a restart, which the job
 *  list does not). Nothing is priced; each links to its scene. */
export const rendersUnfinished = () => apiFetch<{ items: Concept[] }>("/renders/unfinished");
/* ── the manual import lane (operator-gated server-side; the `manual_lane`
   capability only says whether to draw the section): a clip rendered
   anywhere, dropped on its card and filed free ── */
export type LaneItem = {
  concept_id: number;
  title: string;
  shot_n: number;
  prompt: string;
  keyframe_url: string | null;
  duration: number;
  ratio: string;
  lane?: string;
};
/** GET /api/queue/manual — the same waiting shots, addressed to a pair of
 *  hands; a 404 for an account the lane is not open for. There is no model
 *  list: what rendered the clip is free text on the drop. */
export const queueManual = () =>
  apiFetch<{ items: LaneItem[]; lane?: string; import_with?: string }>(
    "/queue/manual",
  );
/** POST /api/queue/manual/{id}/clip — the finished mp4, filed by
 *  ops/render_queue.import_clip as a FREE row. `model` is free text (what
 *  rendered it; the server says "unspecified" when absent); a second drop
 *  is refused (409). */
export const fileLaneClip = (
  id: number,
  file: File,
  claim: { shot_n?: number; model?: string; ratio?: string; duration?: number; anchored?: boolean } = {},
) => {
  const form = new FormData();
  form.append("file", file, file.name);
  if (claim.shot_n != null) form.append("shot_n", String(claim.shot_n));
  if (claim.model) form.append("model", claim.model);
  if (claim.ratio) form.append("ratio", claim.ratio);
  if (claim.duration != null) form.append("duration", String(claim.duration));
  if (claim.anchored != null) form.append("anchored", claim.anchored ? "1" : "0");
  return apiForm<{ ok: boolean; media_url?: string; [k: string]: unknown }>(`/queue/manual/${id}/clip`, form);
};

/** POST /api/refs/upload — reference photos from disk into the shared
 *  bin (JPEG-normalised, content-addressed, mirrored to R2); returns the
 *  URLs to put on a reference card. */
export const uploadRefs = (files: File[]) => {
  const form = new FormData();
  for (const f of files) form.append("photos", f, f.name);
  return apiForm<{ urls: string[]; skipped: number }>("/refs/upload", form);
};

/* the cut (Assemble v0, docs/tasks/CUT_ASSEMBLE_V0.md): a rendered scene's
   clips -> a versioned timeline -> one MP4. Nothing here spends. */
export type CutReady = {
  concept_id: number;
  title: string;
  clips: number;
  poster?: string | null;
  export: { timeline_id: number; version: number; url: string | null } | null;
  /** the shots still on a cheap draft clip (src/drafts.py), each named by
   *  the render id Finish takes */
  drafts?: DraftClip[];
};
export type DraftClip = { shot_n: number; part: number | null; label: string; ref: string; frame: string; model: string };
/** what finishing a draft runs: the effect and its options, the server's */
export type FinishSpec = { effect: string; options: Record<string, OptionValue> };
/** GET /api/cut/ready — scenes whose every shot has a clip, not archived. */
export const cutReady = () =>
  apiFetch<{ ready: CutReady[]; ffmpeg: boolean; captions_burn: boolean; finish?: FinishSpec }>(
    "/cut/ready",
  );
/** POST /api/cut/assemble — a job; its result carries mp4_url + version.
 *  `music` / `voice` are asset:<id> handles from cutUploadMedia. A scene
 *  that is not ready is refused (409) before any job starts. */
export const cutAssemble = (concept_id: number, opts: { music?: string; voice?: string; captions?: string } = {}) =>
  apiFetch<{ job_id: number; clips: number; notes: string[] }>("/cut/assemble", {
    method: "POST",
    body: JSON.stringify({ concept_id, ...opts }),
  });
/** POST /api/cut/media — an uploaded music bed or voiceover -> asset:<id>. */
export const cutUploadMedia = (file: File) => {
  const form = new FormData();
  form.append("file", file, file.name);
  return apiForm<{ handle: string; seconds: number; filename: string }>("/cut/media", form);
};

/* the in-process job registry (clears on restart, and says so) */
export const listJobs = () => apiFetch<{ items: (Job & { cancellable?: boolean })[] }>("/jobs");
export const cancelJob = (id: number) => apiFetch<Job>(`/jobs/${id}/cancel`, { method: "POST", body: "{}" });
export const clearJob = (id: number) => apiFetch<{ deleted: number }>(`/jobs/${id}`, { method: "DELETE" });
/** The priced approve for a scene's keyframes (2026-09-29): nothing is
 *  drawn until this is pressed. 402 out_of_credits when the whole strip
 *  does not fit the balance. */
export const drawKeyframes = (id: number, part?: number) =>
  apiFetch<{ ok: boolean; job_id: number | null; keyframes: KeyframeQuote }>(`/scenes/${id}/keyframes`, {
    method: "POST",
    // one shot's still, priced and drawn alone; no body is the whole strip
    ...(part === undefined ? {} : { body: JSON.stringify({ part }) }),
  });

/* ── creating ── */
export type Job = {
  id: number;
  kind: string;
  label: string;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  progress: number;
  detail: string;
  output?: string | null;
  error?: string | null;
  /** what the job made: a concept id for most kinds, a cut project's uuid
   *  for an editor export (lib/job-feed.ts resultOf reads which) */
  ref_id?: number | string | null;
  started_at?: string | null;
  ended_at?: string | null;
  cancellable?: boolean;
  /** what it spent (2026-10-08, src/charge.metering via app/jobs.py):
   *  credits debited so far -- or, when `charged` is false, what it would
   *  have cost the operator's exempt account -- and what is held right now.
   *  Absent on a job that spent nothing. */
  credits?: number;
  credits_held?: number;
  charged?: boolean;
  /** a finished keyframe job: how many stills it drew (never more than its quote) */
  stills?: number;
  /** a finished cut job (/api/cut/assemble) */
  mp4_url?: string | null;
  version?: number | null;
  /** a finished cut job: how long the joined video runs */
  seconds?: number | null;
  /** what a job filed in the Library, `gen:<id>` (an effect, a free edit,
   *  an assembled cut) */
  asset?: string | null;
  /** an editor export (2026-10-01): what it made, and where */
  format?: "mp4" | "audio" | "still" | "project";
  file_url?: string | null;
  otio_url?: string | null;
  srt_url?: string | null;
  /** a Guide turn (2026-10-08): how far a tool that can say so has come
   *  (the reference hunt), null while nothing can -- the face's arc */
  steps?: { done: number; of: number } | null;
  /** a Guide turn: the answer's own words as the model writes them */
  partial?: string | null;
};
/** POST /api/scenes/run — multipart: idea, count (1–4), refs
 *  (asset photo urls) and files (uploads), exactly what the Jinja
 *  composer posts. */
export const runScenes = (form: FormData) => apiForm<{ job_id: number }>("/scenes/run", form);
/* One Guide turn. A job, not a plain response: the reasoning tier takes
   tens of seconds. Guarded -- see GUARDED_HEADERS. */
export const runCreativeGuide = (form: FormData) =>
  apiForm<{ job_id: number }>("/creative-guide", form, GUARDED_HEADERS);
/* What a Guide turn comes back with (src/creative_guide.Reply). A
   `proposal` is a WRITE the model asked for and nobody has run: the
   thread draws it as a confirm card and the click is runGuideAction.
   `tool_runs` are the READ tools it looked at before answering. */
export type GuideProposal = { tool: string; args: Record<string, unknown>; label: string };
export type GuideToolRun = { tool: string; args: Record<string, unknown>; ok: boolean };
export type GuideReply = {
  message: string;
  choices?: string[];
  brief?: string;
  proposal?: GuideProposal | null;
  tool_runs?: GuideToolRun[];
  /* the assistant pill's fields (assistant=1 on the form; src/lib/assistant.ts
     has their shapes). A plain Guide turn answers them empty. */
  questions?: AssistantQuestion[];
  directions?: AssistantDirection[];
  nudge?: string;
  stage?: string;
  sheet?: ContactSheet | null;
  /** what research_look read this turn: the name, the look, the pages
   *  (lib/look-research.ts) */
  research?: LookResearch[];
};
/** GET /api/clip-models -- the clip models a scene can be rendered on, each
 *  with the catalogue's line and price (src/model_menu.py): the composer
 *  names a proposed renderer off it. The Render card is where one is picked. */
export const getClipModels = () =>
  apiFetch<{ items: { id: string; label: string; note: string; credits: number; seconds: number; frame: string }[] }>("/clip-models");
/* POST /api/creative-guide/act -- the confirm card's click, and the
   ONLY thing that runs a write tool. Guarded like the turn. The server
   re-checks the tool set and refuses any URL in the arguments. */
export const runGuideAction = (
  proposal: GuideProposal,
  /** save_as_project only: the thread as {role, content, tool_calls?} and
   *  the concept ids its sends made -- filed into the new project.
   *  set_project_look only: `project_id`, the project the person is in --
   *  the model never names one; `previous` comes back as the look it
   *  replaced, which is what an Undo puts back */
  extra?: { conversation?: unknown[]; scenes?: number[]; project_id?: number },
) =>
  apiFetch<{ ok: boolean; tool: string; result: string; project?: Project; previous?: string }>("/creative-guide/act", {
    method: "POST",
    headers: GUARDED_HEADERS,
    body: JSON.stringify({ tool: proposal.tool, args: proposal.args, ...(extra || {}) }),
  });
/* POST /api/creative-guide/act for propose_kit_change (2026-10-21): the
   card's Apply. The kit is the one the project the person is in picked;
   `previous` is the spec Apply replaced, which an Undo PATCHes back. */
export const runKitChange = (proposal: GuideProposal, projectId: number) =>
  apiFetch<{ ok: boolean; tool: string; result: string; kit: Kit; previous: KitSpec }>("/creative-guide/act", {
    method: "POST",
    headers: GUARDED_HEADERS,
    body: JSON.stringify({ tool: proposal.tool, args: proposal.args, project_id: projectId }),
  });
/** create_project / save_as_project: the Guide's two ways a project is made */
export const PROJECT_TOOLS = ["create_project", "save_as_project"];
export const isProjectTool = (tool?: string) => !!tool && PROJECT_TOOLS.includes(tool);
export const getJob = (id: number) => apiFetch<Job>(`/jobs/${id}`);
/** DELETE /api/jobs -- every finished job of yours, at once (the tray) */
export const clearFinishedJobs = () => apiFetch<{ cleared: number }>("/jobs", { method: "DELETE" });

/* THE JOB FEED (2026-10-08). The studio keeps ONE connection to
   /api/jobs/stream (lib/jobs.ts), and while it is live every wait below
   rides on it: a job's progress, its streamed words and its end arrive as
   they happen, with no request per tick. When the stream is down or never
   came up, the same waits poll exactly as they always did. lib/jobs.ts
   plugs itself in here rather than this module importing it, so the fetch
   layer stays free of the stream. */
export type JobFeed = {
  /** true while the stream is connected and has said hello */
  live(): boolean;
  /** every version of job `id` the stream holds or delivers; `lost` once if
   *  it drops before the job ends. Returns the unsubscribe. */
  watch(id: number, onJob: (job: Job) => void, lost: () => void): () => void;
};
let jobFeed: JobFeed | null = null;
export const setJobFeed = (feed: JobFeed | null) => {
  jobFeed = feed;
};
const JOB_ENDED = ["done", "failed", "cancelled"];

/** Follow job `id` until it ends -- from the stream while it is live, else
 *  by polling every `everyMs` (which may depend on what the job just said).
 *  Resolves to the finished job, or null once `stopped()` says so. The one
 *  wait every caller goes through. */
export async function followJob(
  id: number,
  onTick?: (job: Job) => void,
  opts: { everyMs?: number | ((job: Job) => number); stopped?: () => boolean } = {},
): Promise<Job | null> {
  const { everyMs = 1500, stopped } = opts;
  if (jobFeed?.live()) {
    const feed = jobFeed;
    const fed = await new Promise<Job | null | "lost">((resolve) => {
      let unwatch: (() => void) | null = null;
      let stopCheck: ReturnType<typeof setInterval> | null = null;
      let settled = false;
      const finish = (value: Job | null | "lost") => {
        if (settled) return;
        settled = true;
        if (stopCheck) clearInterval(stopCheck);
        unwatch?.();
        resolve(value);
      };
      // a Stop has to end the wait at once, whatever the server does
      if (stopped) stopCheck = setInterval(() => stopped() && finish(null), 200);
      unwatch = feed.watch(
        id,
        (job) => {
          if (settled) return;
          onTick?.(job);
          if (JOB_ENDED.includes(job.status)) finish(job);
        },
        () => finish("lost"),
      );
      if (settled) unwatch();
    });
    if (fed !== "lost") return fed;
  }
  for (;;) {
    if (stopped?.()) return null;
    const job = await getJob(id);
    if (stopped?.()) return null;
    onTick?.(job);
    if (JOB_ENDED.includes(job.status)) return job;
    await new Promise((r) => setTimeout(r, typeof everyMs === "function" ? everyMs(job) : everyMs));
  }
}

/* `everyMs` may depend on what the job just said: a Guide turn whose
   answer is arriving is polled faster than one still thinking (only while
   the stream is down -- on the stream every word arrives as it is said). */
export async function waitForJob(
  id: number,
  onTick?: (job: Job) => void,
  everyMs: number | ((job: Job) => number) = 1500,
): Promise<Job> {
  return (await followJob(id, onTick, { everyMs })) as Job;
}

/* ── presets (the camera chips) ── */
/** `tried` / `kept`: how many outputs this account made with the preset,
 *  and how many of those were kept (src/outcomes.py). Absent on a server
 *  that does not count them. */
export type Preset = { id: string; label: string; how: string; tried?: number | null; kept?: number | null };
export const getPresets = () =>
  apiFetch<{ items: Preset[]; enhance_system: string }>("/presets");
/** GET /api/presets/counts — this account's tried / kept per preset id. */
export const getPresetCounts = () =>
  apiFetch<{ counts: Record<string, { tried: number; kept: number }> }>("/presets/counts");

/* ── skills (the brain's recipes; lib/skills.ts) ── */
export const getSkills = () => apiFetch<{ items: Skill[] }>("/skills");

/* ── effects (src/effects.py; lib/effects.ts) ── */
export type EffectsCatalogue = {
  items: Effect[];
  categories: { id: string; label: string }[];
  /** the server can run them */
  ready: boolean;
  /** this account is not charged */
  exempt: boolean;
};
export const getEffects = () => apiFetch<EffectsCatalogue>("/effects");
export type EffectRequest = {
  effect: string;
  sources: string[];
  prompt: string;
  options: Record<string, OptionValue>;
  /** FINISH a draft: the one source is a scene's draft clip, and what the
   *  upscale makes is put on that shot in its place (src/drafts.py) */
  finish?: boolean;
};
export type EffectQuote = { effect: string; label: string; output: string; credits: number; charged: boolean };
/** what it costs, in credits; spends nothing */
export const quoteEffect = (body: EffectRequest) =>
  apiFetch<EffectQuote>("/effects/quote", { method: "POST", body: JSON.stringify(body) });
/** the click on the priced card: `expect_credits` is what that card showed */
export const runEffect = (body: EffectRequest & { expect_credits: number }) =>
  apiFetch<{ job_id: number; credits: number; charged: boolean }>("/effects/run", {
    method: "POST",
    body: JSON.stringify(body),
  });

/* ── a talking photo (src/talking_photo.py; lib/talking-photo.ts) ── */
export const getTalkMenu = () => apiFetch<TalkMenu>("/talking-photo");
export type VoiceBody = { script: string; voice: string; language: string };
export type VoiceQuote = { voice: string; language: string | null; characters: number; credits: number; charged: boolean };
/** what reading the script aloud costs; spends nothing */
export const quoteVoice = (body: VoiceBody) =>
  apiFetch<VoiceQuote>("/talking-photo/voice/quote", { method: "POST", body: JSON.stringify(body) });
/** the Preview click: a job whose result names the voice (`audio`), its
 *  measured `seconds` and where to play it (`output`) */
export const runVoice = (body: VoiceBody & { expect_credits: number }) =>
  apiFetch<{ job_id: number; credits: number; charged: boolean }>("/talking-photo/voice/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
export type TalkBody = { photo: string; audio: string; prompt: string; consent: boolean; project_id?: number };
export type TalkQuote = {
  credits: number;
  charged: boolean;
  audio_seconds: number;
  billed_seconds: number;
  audio_cap: number;
  photo_size: [number, number];
};
/** what this photo speaking this voice costs; spends nothing */
export const quoteTalk = (body: TalkBody) =>
  apiFetch<TalkQuote>("/talking-photo/quote", { method: "POST", body: JSON.stringify(body) });
/** the Render click, at the price the card showed */
export const runTalk = (body: TalkBody & { expect_credits: number }) =>
  apiFetch<{ job_id: number; credits: number; charged: boolean }>("/talking-photo/run", {
    method: "POST",
    body: JSON.stringify(body),
  });

/** A free edit the brain proposed (POST /api/quick-edit): a new shape or a
 *  range, made on the studio's server for no credits, as a job. `source`
 *  is a gen:<id> or asset:<id>, never an address. */
export type QuickEditRequest = {
  tool: "reformat" | "trim_clip";
  source: string;
  aspect?: string;
  fit?: string;
  start?: number;
  end?: number;
  project_id?: number;
};
export const runQuickEdit = (body: QuickEditRequest) =>
  apiFetch<{ job_id: number; credits: number }>("/quick-edit", { method: "POST", body: JSON.stringify(body) });

/* ── the account switch and sign-out live at the API root ── */
/** POST /account/{slug} THROUGH THE PROXY (API_URL is empty in production,
 *  so this is our own origin and the `phantra_account` cookie lands
 *  first-party -- the handoff lesson). The route answers 303; `manual`
 *  keeps fetch from following it into a page nobody reads. Resolves once
 *  the cookie is set; the caller refetches /api/me, which is what says the
 *  switch took. */
export async function switchAccount(slug: string) {
  const body = new FormData();
  body.append("next", "/studio");
  await fetch(`${API_URL}/account/${encodeURIComponent(slug)}`, {
    method: "POST",
    credentials: "include",
    body,
    redirect: "manual",
  });
}

/* "A scene's render moved": fired when a render or its keyframes are
   approved, when their job ends, and when a scene is removed or put back.
   The scene lists, the canvas, Renders and the balance listen. (The name
   is from when the Queue's rail badge was the listener.) */
export const QUEUE_EVENT = "phantra:queue";
export const announceQueueChange = () =>
  window.dispatchEvent(new Event(QUEUE_EVENT));

/* ── credits (2026-09-25) ──
   GET /api/billing/balance -- src/billing.balance, the numbers the shell's
   credit pill and the Queue read. `available` is spendable NOW (lots minus
   holds still outstanding); `outstanding` is what renders in flight hold.
   `exempt` is an operator account the ledger never charges: its pill says
   so instead of a number that would never move. `portal` = a Stripe
   customer exists, so "Manage billing" has somewhere to go. */
export type CreditLot = {
  id: number;
  kind: string;
  credits: number;
  remaining: number;
  granted_at: string;
  expires_at: string | null;
};
export type Balance = {
  available: number;
  outstanding: number;
  plan: { key: string; name: string; tier: string; credits: number; monthly_usd: number } | null;
  exempt: boolean;
  lots: CreditLot[];
  schedules: { plan: string; months_released: number; months_total: number; next_release_at: string | null }[];
  checkout_configured: boolean;
  yearly_configured: boolean;
  portal: boolean;
  /** what a still costs on THIS server (app/billing.action_prices) */
  /** `sheet`: an element sheet, always Nano Banana Pro at 2K (2026-10-11) */
  prices?: { still: number; sheet?: number };
  /** the workspace these credits belong to: the person's FIRST one,
   *  whichever is open (lib/credits `countedElsewhere`) */
  account?: { id: number; label: string } | null;
};
export const getBalance = () => apiFetch<Balance>("/billing/balance");
/* Settings → Usage (2026-10-11): where the credits went. One row per
   movement of the ledger, newest first, paged by id; the first page also
   carries the 30-day summary. Credits only (src/credit_history.py). */
export const getCreditHistory = (before?: number | null, limit = 50) =>
  apiFetch<CreditHistory>(`/billing/history?limit=${limit}${before ? `&before=${before}` : ""}`);
/** fired after anything that moves credit: an approve takes a hold, a
 *  finished render settles it. The shell re-reads the balance on it. */
export const BALANCE_EVENT = "phantra:balance";
export const announceBalanceChange = () => window.dispatchEvent(new Event(BALANCE_EVENT));
/** Re-read the balance once `jobId` has ended (2026-10-08). A job that
 *  draws a still or renders a clip settles -- or releases -- its hold when
 *  it finishes, and the shell hears about it from nothing else; a caller
 *  that is not already watching the job hands it here. Polls until the job
 *  is terminal, gives up quietly on a lost connection (announcing once, so
 *  the pill is re-read anyway), and outlives the component that asked. */
export function announceBalanceWhenDone(jobId: number, every = 2500): void {
  followJob(jobId, undefined, { everyMs: every })
    .then(() => announceBalanceChange())
    .catch(() => announceBalanceChange());
}

/* ── projects (2026-09-28) ──
   One brief and one memory per piece of work (src/projects.py). The
   memory is what the project LEARNED -- picks, passes with their reason,
   hand edits -- and every Create inside the project is written against
   the brief plus that memory, which is how its renders stay consistent. */
export type ProjectMemory = {
  kind: "pick" | "pass" | "edit" | "note";
  text: string;
  concept_id: number | null;
  at: string;
};
export type Project = {
  id: number;
  title: string;
  brief: string;
  /** the project's look (2026-10-02); "" imposes none */
  look?: string;
  /** the Explore / Make switch (2026-10-11, lib/explore.ts): true while a
   *  send inside the project only talks. Absent or false is Make. */
  explore?: boolean;
  memory: ProjectMemory[];
  archived: boolean;
  created_at: string;
  updated_at: string;
  concepts?: number;
  picked?: number;
  rendered?: number;
  /** the board card's picture: the newest scene's still, else its first
   *  reference, minted for the browser (null when it has no scene yet) */
  cover?: string | null;
  /** the cover's 480px tile, when one exists (app/api.py _ref_thumbs) */
  cover_thumb?: string | null;
};
/* PROJECTS ARE MADE THROUGH THE GUIDE (2026-10-07, Mike's call): there is
   no create form. The pill or the composer's brain proposes create_project
   / save_as_project and the confirm card posts runGuideAction. */
export const listProjects = (archived = false) =>
  apiFetch<{ items: Project[] }>(`/projects${archived ? "?archived=true" : ""}`);
export const getProject = (id: number) => apiFetch<Project>(`/projects/${id}`);
/** Where a project stands (src/projects.py standing): counts, and the one
 *  line Vesper opens with when it is reopened. Free; no model. */
export type ProjectStanding = {
  project_id: number;
  scenes: number;
  rendered: number;
  part: number;
  ready: number;
  photo: number;
  line: string;
};
export const getProjectStanding = (id: number) => apiFetch<ProjectStanding>(`/projects/${id}/standing`);
export const updateProject = (
  id: number,
  patch: { title?: string; brief?: string; look?: string; explore?: boolean },
) =>
  apiFetch<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
export const archiveProject = (id: number, archived = true) =>
  apiFetch<{ ok: boolean }>(`/projects/${id}/archive`, {
    method: "POST",
    body: JSON.stringify({ archived }),
  });
export const forgetProjectMemory = (id: number, at: string) =>
  apiFetch<{ ok: boolean; removed: boolean }>(`/projects/${id}/forget`, {
    method: "POST",
    body: JSON.stringify({ at }),
  });
/** what deleting the project would leave detached (the confirm lists the
 *  unrendered ones: they have no board to appear on afterwards) */
export const projectScenes = (id: number) =>
  apiFetch<{ items: { id: number; title: string; rendered: boolean }[] }>(`/projects/${id}/scenes`);
/** Delete for good: brief, look, memory and chat history. Its scenes are
 *  detached, never deleted, so a rendered clip stays on Assets. */
export const deleteProject = (id: number) =>
  apiFetch<{ ok: boolean; detached: number; messages: number }>(`/projects/${id}`, {
    method: "DELETE",
    headers: GUARDED_HEADERS,
  });
/** One turn of a project's chat history, as src/projects.py stores it. */
export type ProjectMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  /** what the reply carried beside its words (proposal, chips, directions…) */
  tool_calls: Partial<GuideReply> | null;
  created_at: string;
};
export const projectMessages = (id: number, before?: number) =>
  apiFetch<{ items: ProjectMessage[]; has_more: boolean }>(
    `/projects/${id}/messages${before ? `?before=${before}` : ""}`,
  );

/* Where a scene's canvas opens (2026-10-07): /studio/scene/<id> resolves
   it -- into its project's workspace when it is filed under one, else the
   canvas alone (a single video made outside any project). The ONE place a
   page builds a scene link, so no page names the retired Director route. */
export const sceneHref = (id: number, shot?: number) => `/studio/scene/${id}${shot ? `?shot=${shot}` : ""}`;
export const workspaceHref = (project: number, scene?: number, shot?: number) => {
  const params = new URLSearchParams();
  if (scene) params.set("scene", String(scene));
  if (scene && shot) params.set("shot", String(shot));
  const qs = params.toString();
  return `/studio/projects/${project}${qs ? `?${qs}` : ""}`;
};

/* The project the Studio composer is writing inside. Carried as ?project=
   from the Projects page and remembered per browser so a reload keeps it;
   clearing it is one click on the composer's chip. */
export const ACTIVE_PROJECT_KEY = "phantra.project";
export function rememberActiveProject(id: number | null) {
  try {
    if (id) localStorage.setItem(ACTIVE_PROJECT_KEY, String(id));
    else localStorage.removeItem(ACTIVE_PROJECT_KEY);
  } catch {
    /* private window: the ?project= param still works */
  }
}
export function recallActiveProject(): number | null {
  try {
    const v = Number(localStorage.getItem(ACTIVE_PROJECT_KEY));
    return Number.isFinite(v) && v > 0 ? v : null;
  } catch {
    return null;
  }
}

/* ── the composer's IMAGE output (2026-10-02) ──
   POST /api/generate/run, output=image: preset + prompt + the same two
   reference fields Create sends (`files`, `asset_photos`) -> one Nano
   Banana still saved as a one-shot concept. Not mutation_header-guarded
   (the Create route beside it is not either). `aspect` is optional and
   allowlisted server-side. */
/* GET /api/image-models: what a still can be drawn on, with what one
   costs -- the composer's picker, and the pill's step card price line */
export type ImageModels = { items: { id: string; label: string; note: string; credits: number }[]; default: string };
export const getImageModels = () => apiFetch<ImageModels>("/image-models");
export const runImage = (form: FormData) =>
  apiForm<{ job_id: number; image_refs: number; video_refs: number }>("/generate/run", form);

/** GET /api/concepts/{id} — the card plus its shots; the composer reads
 *  the still off the card (reference_image) or the scene's timeline. */
export type ConceptDetail = Concept & {
  duration?: number | null;
  shots?: { n: number; reference_image?: string | null; timeline?: Timeline | null }[];
};
export const getConceptDetail = (id: number) => apiFetch<ConceptDetail>(`/concepts/${id}`);

// ---------------------------------------------------------------------------
// publishing (2026-10-11, src/publish_review.py): a draft prepared by Claude
// or a studio button, reviewed and sent by the person on /studio/publish/[id]
// ---------------------------------------------------------------------------

export type PublishCreator = {
  username: string;
  nickname: string;
  avatar_url: string;
  privacy_options: string[];
  comment_disabled: boolean;
  duet_disabled: boolean;
  stitch_disabled: boolean;
  max_seconds: number | null;
};

export type PublishSession = {
  session_id: string;
  platform: string;
  status: "draft" | "posting" | "published" | "failed" | "cancelled" | "expired";
  source: string;
  media_url: string;
  media_kind: string;
  seconds: number | null;
  ai_generated: boolean;
  caption: string;
  created_via: "mcp" | "studio";
  expires_at: string;
  choices: Record<string, unknown> | null;
  result: { publish_id?: string; post_id?: string; step?: string; error?: string } | null;
  media_problem?: string | null;
  creator?: PublishCreator | null;
  creator_problem?: string | null;
  declarations?: { default: string; branded: string };
  caption_max?: number;
  poll_problem?: string;
};

export type PublishChoices = {
  caption: string;
  privacy_level: string | null;
  allow_comment: boolean;
  allow_duet: boolean;
  allow_stitch: boolean;
  commercial: { enabled: boolean; your_brand: boolean; branded_content: boolean };
  is_aigc: boolean;
  consent: boolean;
};

export async function getPublishSession(id: string): Promise<PublishSession> {
  return apiFetch<PublishSession>(`/publish/${encodeURIComponent(id)}`);
}

export async function submitPublish(id: string, choices: PublishChoices): Promise<PublishSession> {
  return apiFetch<PublishSession>(`/publish/${encodeURIComponent(id)}/submit`, {
    method: "POST",
    body: JSON.stringify(choices),
  });
}

export async function cancelPublish(id: string): Promise<PublishSession> {
  return apiFetch<PublishSession>(`/publish/${encodeURIComponent(id)}/cancel`, { method: "POST" });
}

/* ── social accounts (2026-10-22, app/social_routes.py) ──
   A person's own Instagram / Discord (later TikTok, YouTube, Facebook,
   LinkedIn, Reddit), connected to the workspace through the platform's
   own consent screen. Connecting is a top-level navigation to the API
   origin (`{AUTH_ORIGIN}${start_url}`), the way sign-in goes; nothing here
   spends, and no token ever reaches the page. */
export type SocialProvider = {
  id: string;
  name: string;
  /** this server has the platform's app keys */
  configured: boolean;
  /** what connecting means, in words: "a channel in a Discord server you manage" */
  connects: string;
  /** a step still to do after the consent screen (Discord: "channel") */
  pending_step: string | null;
  start_url: string;
  redirect_uri: string;
};
export type SocialConnection = {
  id: number;
  provider: string;
  provider_name: string;
  external_id: string;
  display_name: string;
  handle: string;
  avatar_url: string;
  /** the one line the card draws: "Phantra HQ · #showcase", "@phantra.ai" */
  label: string;
  status: "connected" | "pending" | "reconnect" | "expired";
  pending: string | null;
  expires_at: string | null;
  scopes: string[];
  meta: Record<string, unknown>;
  connected_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  /** the hours this account likes to post, by weekday, in its zone (2026-10-22) */
  posting_times: { tz: string; days: Record<string, string[]> };
};
export type SocialOption = { id: string; label: string; hint?: string; kind?: string };

export const getSocialProviders = () =>
  apiFetch<{ providers: SocialProvider[]; vault_ready: boolean }>("/social/providers");
export const getSocialConnections = () => apiFetch<{ connections: SocialConnection[] }>("/social/connections");
export const getSocialOptions = (id: number) => apiFetch<{ options: SocialOption[] }>(`/social/connections/${id}/options`);
export const pickSocialOption = (id: number, choice: string) =>
  apiFetch<SocialConnection>(`/social/connections/${id}/pick`, { method: "POST", body: JSON.stringify({ choice }) });
export const disconnectSocial = (id: number) =>
  apiFetch<{ ok: true; id: number }>(`/social/connections/${id}`, { method: "DELETE" });

/* ── posts (2026-10-22, app/post_routes.py) ──
   One clip or still, to one connected account, at one time. Creating one
   sends nothing: the publish worker does, on the clock. Nothing spends. */
export type PostState = "draft" | "queued" | "publishing" | "published" | "error" | "cancelled";
export type Post = {
  id: number;
  connection_id: number;
  provider: string;
  provider_name: string;
  group_id: string;
  publish_at: string | null;
  state: PostState;
  caption: string;
  source_ref: string;
  media: { ref?: string; media_url?: string; kind?: string; seconds?: number | null };
  settings: Record<string, unknown>;
  concept_id: number | null;
  project_id: number | null;
  release_id: string | null;
  release_url: string | null;
  error: string | null;
  creation_method: string;
  attempts: number;
  pending: boolean;
  published_at: string | null;
  video_id: number | null;
  created_at: string | null;
  updated_at: string | null;
  events?: { at: string | null; event: string; detail: string }[];
};
export type NewPost = {
  connection_id: number;
  source: string;
  caption?: string;
  /** ISO 8601; empty = now */
  publish_at?: string | null;
  settings?: Record<string, unknown>;
  draft?: boolean;
  project_id?: number | null;
  group_id?: string | null;
};
export const listPosts = (params: { start?: string; end?: string; state?: PostState } = {}) => {
  const q = new URLSearchParams();
  if (params.start) q.set("start", params.start);
  if (params.end) q.set("end", params.end);
  if (params.state) q.set("state", params.state);
  const qs = q.toString();
  return apiFetch<{ posts: Post[] }>(`/posts${qs ? `?${qs}` : ""}`);
};
export const createPost = (body: NewPost) => apiFetch<Post>("/posts", { method: "POST", body: JSON.stringify(body) });
export const getPost = (id: number) => apiFetch<Post>(`/posts/${id}`);
export const movePost = (id: number, publish_at: string | null) =>
  apiFetch<Post>(`/posts/${id}/date`, { method: "PUT", body: JSON.stringify({ publish_at }) });
export const setPostState = (id: number, state: "queued" | "draft" | "cancelled") =>
  apiFetch<Post>(`/posts/${id}/state`, { method: "POST", body: JSON.stringify({ state }) });
export const patchPost = (id: number, body: { caption?: string; settings?: Record<string, unknown> }) =>
  apiFetch<Post>(`/posts/${id}`, { method: "PATCH", body: JSON.stringify(body) });
export const deletePost = (id: number) => apiFetch<{ ok: true; id: number }>(`/posts/${id}`, { method: "DELETE" });

/* ── the calendar (2026-10-22, docs/tasks/task-calendar.md) ── */
/** One clip to several accounts at one press: one row each, one group_id.
 *  All or nothing: a refusal on any account writes no row. */
export type NewPostGroup = {
  connection_ids: number[];
  source: string;
  caption?: string;
  /** per-connection words, when a tab holds its own */
  captions?: Record<number, string>;
  publish_at?: string | null;
  settings?: Record<string, unknown>;
  draft?: boolean;
  project_id?: number | null;
};
export const createPostGroup = (body: NewPostGroup) =>
  apiFetch<{ posts: Post[]; group_id: string | null }>("/posts/group", { method: "POST", body: JSON.stringify(body) });
/** the connection's first free posting time, or null when it has none */
export const nextFreeSlot = (connection_id: number, after?: string) => {
  const q = new URLSearchParams({ connection_id: String(connection_id) });
  if (after) q.set("after", after);
  return apiFetch<{ slot: { publish_at: string; tz: string } | null }>(`/posts/next-slot?${q}`);
};
export type FreeSlot = { connection_id: number; provider: string; label: string; publish_at: string };
export const freeSlots = (start: string, end: string) =>
  apiFetch<{ slots: FreeSlot[] }>(`/posts/free-slots?${new URLSearchParams({ start, end })}`);
export type FeedItem = { id: string; kind: "image" | "video"; thumb: string; url: string; at: string; caption: string };
export type Feed = { connection: SocialConnection; offered: boolean; posts: Post[]; recent: FeedItem[]; note: string };
export const getFeed = (connection_id: number) =>
  apiFetch<Feed>(`/posts/feed?${new URLSearchParams({ connection_id: String(connection_id) })}`);
/** {"tz": "America/New_York", "days": {"mon": ["09:00", "18:30"], ...}} */
export type PostingTimes = { tz: string; days: Record<string, string[]> };
export const setPostingTimes = (connection_id: number, times: PostingTimes) =>
  apiFetch<SocialConnection>(`/social/connections/${connection_id}/posting-times`, { method: "PUT", body: JSON.stringify(times) });

/* ── brand kits (2026-10-20, app/brand_routes.py) ──
   A kit belongs to the account; a project picks one. Nothing here spends:
   the end card is drawn by the API with Pillow, the preview composes text. */

export type KitList = { kits: Kit[]; roles: Record<string, { label: string; max: number }> };
export const listBrandKits = () => apiFetch<KitList>("/brand-kits");
export const getBrandKit = (id: number) => apiFetch<Kit>(`/brand-kits/${id}`);
export const createBrandKit = (name: string, spec?: Partial<KitSpec>) =>
  apiFetch<Kit>("/brand-kits", { method: "POST", body: JSON.stringify({ name, spec: spec ?? {} }) });
/** POST /api/brand-kits/import -- a NEW kit read off a website, as a job
 *  (src/brand_import.py); the finished job carries kit_id and notes */
export const importBrandKit = (url: string) =>
  apiFetch<{ job_id: number }>("/brand-kits/import", { method: "POST", body: JSON.stringify({ url }) });
export const updateBrandKit = (id: number, body: { name?: string; spec?: KitSpec }) =>
  apiFetch<Kit>(`/brand-kits/${id}`, { method: "PATCH", body: JSON.stringify(body) });
export const duplicateBrandKit = (id: number) =>
  apiFetch<Kit>(`/brand-kits/${id}/duplicate`, { method: "POST" });
export const deleteBrandKit = (id: number) =>
  apiFetch<{ deleted: number }>(`/brand-kits/${id}`, { method: "DELETE" });
export const restoreBrandKit = (id: number) =>
  apiFetch<Kit>(`/brand-kits/${id}/restore`, { method: "POST" });
export function uploadKitFile(id: number, role: string, file: Blob, filename: string, licensed = false) {
  const form = new FormData();
  form.append("role", role);
  form.append("file", file, filename);
  if (licensed) form.append("licensed", "1");
  return apiForm<{ added: number; kit: Kit }>(`/brand-kits/${id}/assets`, form);
}
export const removeKitFile = (id: number, fileId: number) =>
  apiFetch<{ removed: number; kit: Kit | null }>(`/brand-kits/${id}/assets/${fileId}`, { method: "DELETE" });
export const endCardUrl = (id: number, aspect: string, hash: string) =>
  `${API_URL}/api/brand-kits/${id}/end-card.png?aspect=${encodeURIComponent(aspect)}&v=${hash}`;

export type ProjectKit = {
  project_id: number;
  picked?: number | null;
  brand_kit: { id: number; name: string; palette?: { hex: string; role: string }[] } | null;
};
export const getProjectKit = (projectId: number) => apiFetch<ProjectKit>(`/projects/${projectId}/brand-kit`);
export const setProjectKit = (projectId: number, kitId: number | null) =>
  apiFetch<ProjectKit>(`/projects/${projectId}/brand-kit`, {
    method: "PUT",
    body: JSON.stringify({ brand_kit_id: kitId }),
  });
