# Task: give the Premiere and Resolve panels their own repos

**For:** Claude Code on Mike's Mac. **From:** a Cowork session, 2026-10-23. **Mike's ask:**
"get these their own repos up and running"; then (2026-10-23): **"i do want a license on them
and to be private, people will be able to download them to plugin eventually"**. So both repos
are PRIVATE, both carry a proprietary license (already committed), and people will get the
panels as downloads from Phantra, never from GitHub. The cloud session can't create GitHub
repos, so this runs here, with Mike's own `gh`.

Read first: `CLAUDE.md`, `docs/tasks/task-premiere-plugin.md` (on branch `claude/premiere-plugin`,
PR #457) and `docs/tasks/task-resolve-plugin.md` (on `claude/resolve-plugin`, PR #462).

## State right now

- **The server half is in this repo and stays here.** PR #457 (the `/plugin/v1` API, sign-in by
  code, `/studio/link`, the Apps card) and PR #462 (stacked on it: `resolve` as a sign-in client).
  Neither holds any panel code. Merge #457 first, then #462. Not part of this task.
- **The panels have no GitHub repo yet.** Their full git history is in two bundles here, in a
  gitignored folder (`data/_scratch_*`):

  | Bundle | Branch | HEAD | sha256 |
  |---|---|---|---|
  | `data/_scratch_plugins/phantra-premiere-plugin.bundle` | `main` | `66c77a7` (3 commits) | `df5c267b…187bf7e` |
  | `data/_scratch_plugins/phantra-resolve-plugin.bundle` | `main` | `8858edc` (2 commits) | `171d0a54…5c82337` |

  Full hashes: `df5c267b8b7aad10ef07a11bb2062edea38a9db79ca511e602bb6e9cb187bf7e` and
  `171d0a54c3554777194bf8950bb42e8eb3698198a47da64d632e7b1285c82337`. Each bundle was cloned in
  the cloud and on this Mac; tests in the cloud: Premiere 9 pass, Resolve 61 pass.
- **The license is in both already** (the last commit in each): `LICENSE` is a proprietary
  "Phantra Plugin License" (install and use with your own Phantra account; no copying,
  redistributing, modifying or reverse engineering; no warranty), `package.json` says
  `"license": "SEE LICENSE IN LICENSE"`, the README has a License section, and the Resolve
  installer copies `LICENSE` into the installed plugin. It was written by an AI, not a lawyer:
  Mike may have it reviewed, and the copyright line names "Phantra (phantra.ai)", which should
  become the legal owner's name once Phantra has one.
- **Copies to clean up afterwards**, NOT gitignored (they show as untracked in `git status`;
  never `git add` them): `data/phantra-premiere-plugin.zip`, `data/phantra-resolve-plugin.zip`,
  `data/phantra-resolve-plugin/` (an unzipped install copy of the Resolve panel).
- The sibling plugin repos for reference: `zeropage-onryo/phantra-claude-plugin` and
  `zeropage-onryo/phantra-chatgpt-plugin`, both cloned at `../`. Those two are PUBLIC (they are
  skills for directory listings); these two are PRIVATE on purpose.

## Rules for the run

No renders and no paid calls. Nothing in `src/mcp_server.py`, `app/mcp_mount.py` or
`app/mcp_auth.py` changes. Never print a token. Tests before every push. Ask Mike before any
step marked **(ask)**.

## Steps

1. **Check the tools.** `gh auth status` (logged in, with access to `zeropage-onryo`);
   `gh repo view zeropage-onryo/phantra-premiere-plugin` and `.../phantra-resolve-plugin` should
   both say not found. If one exists already, stop and tell Mike: never push over a repo that
   has content you didn't put there.
2. **Restore each repo from its bundle**, beside the other plugin repos:
   ```bash
   cd ~/Documents
   for r in phantra-premiere-plugin phantra-resolve-plugin; do
     [ -e "$r" ] && { echo "$r already exists: stop"; break; }
     shasum -a 256 "PRODUCTION PIPLINE .GIT/data/_scratch_plugins/$r.bundle"
     git clone "PRODUCTION PIPLINE .GIT/data/_scratch_plugins/$r.bundle" "$r"
     git -C "$r" remote remove origin
     (cd "$r" && git log --oneline -1 && npm test)
   done
   ```
   The hashes must match the table, HEADs must be `1bec3a3` and `86eac44`, and the tests must pass.
3. **Create the repos as PRIVATE and push** (Mike's call, already made):
   ```bash
   cd ~/Documents/phantra-premiere-plugin
   gh repo create zeropage-onryo/phantra-premiere-plugin --private \
     --description "Phantra for Adobe Premiere Pro: make AI images and video and bring your Phantra Library onto the timeline." \
     --source . --remote origin --push
   cd ~/Documents/phantra-resolve-plugin
   gh repo create zeropage-onryo/phantra-resolve-plugin --private \
     --description "Phantra for DaVinci Resolve Studio: make AI images and video and bring your Phantra Library into the Media Pool and onto the timeline." \
     --source . --remote origin --push
   ```
   Check: `git -C <repo> status -sb` shows `main...origin/main`, and
   `gh repo view zeropage-onryo/<repo> --json visibility,defaultBranchRef` shows PRIVATE and main.
4. **CI in each repo (ask), one branch and PR per repo:** `.github/workflows/test.yml` running
   `npm test` on Node 20 for pull requests and pushes to main (no secrets, no network). Merge
   only once its first run is green. (Actions on a private repo use the account's included
   minutes; these suites take seconds.)
5. **Point this repo's docs at the new repos**, as one commit on each PR branch (pull first;
   other sessions push to these):
   - On `claude/premiere-plugin` (#457): `docs/tasks/task-premiere-plugin.md`, "Panel:
     `phantra-premiere-plugin` (not yet pushed)" becomes the repo's URL.
   - On `claude/resolve-plugin` (#462): `docs/tasks/task-resolve-plugin.md` ("not on GitHub
     yet", "a public repo (Mike's to create)") becomes the URL.
   - `CLAUDE.md`'s "The plugins" line lists the four plugin repos. It is the same file every
     session reads: put this on its own small branch and PR, not on #457 or #462.
   - `docs/tasks/HANDOFF-resolve-2026-10-22.md` (untracked here): its step 3 points at
     `data/phantra-resolve-plugin/`; make that `~/Documents/phantra-resolve-plugin/`.
6. **Clean up (ask)** once steps 2 and 3 are checked: delete `data/phantra-premiere-plugin.zip`,
   `data/phantra-resolve-plugin.zip`, `data/phantra-resolve-plugin/` and
   `data/_scratch_plugins/`. `git status` in this repo then shows none of them.
7. **Report to Mike:** the two repo URLs, the CI result, the PR numbers from steps 4 and 5, and
   that installing the Resolve panel is now `~/Documents/phantra-resolve-plugin/install.command`
   (quit Resolve first).

## Decided by Mike (2026-10-23)

- **Private** repos.
- **A license**: the proprietary one above, already committed.

## Part 2: people can download the panels (Mike, 2026-10-23: "add that to part of the job")

A private repo can't serve a download, so each panel gets a release build, the build goes up
to the media bucket under `site/downloads/`, and a page on phantra.ai links it. Same rules as
Part 1, plus: **the bucket and the live site are live data** (CLAUDE.md: report first, then
write only on Mike's word), and nothing is published that hasn't run in its host app.

**Gates, before any upload (check each, and stop with the reason if one isn't met):**
- Part 1 is done (both repos up, private).
- PR #457 and then #462 are merged and DEPLOYED (`curl -s https://api.phantra.ai/plugin/v1/me`
  answers 401 `unauthorized`, not 404), and `QUOTE_SIGNING_SECRET` is set on Fly
  (`fly secrets list -a phantra-api`, names only). Without that secret every spending tool in
  the panel answers 503 `cannot_approve`.
- **The Resolve panel was run inside Mike's Resolve Studio** and the free checks passed: sign in,
  Library, Import, Insert at the playhead, Clip on the timeline, Frame at playhead, a price
  shown and CANCELLED in the confirm window. Fix anything that fails first, with a test in
  `test/resolve.test.js`.
- **The Premiere panel is NOT published** until someone runs it in Premiere Pro 25.6+ (Mike has
  no Premiere). Build its `.ccx` (step 9) but keep it off the page.

8. **Resolve release build** (a branch + PR in `phantra-resolve-plugin`): `scripts/build-release.sh`
   makes `dist/phantra-resolve-plugin-<version>.zip` (version from `package.json`, which must
   match `manifest.xml`'s `<Version>`): the files `install.command` copies, plus
   `install.command`, `uninstall.command`, `README.md` and `LICENSE`. No `test/`, no `docs/`, no
   `WorkflowIntegration.node` (it always comes from the person's own Resolve). It prints the
   zip's sha256. Test: unzip it into a temp folder, run its `install.command` against a fake
   `/Library` (`PHANTRA_RESOLVE_PLUGINS=... PHANTRA_RESOLVE_DEVELOPER=...`, see the installer),
   and check the installed copy holds every file `main.js` requires.
   - **(ask)** A signed and notarized `.pkg` instead of a zip needs an Apple Developer ID
     ($99/year, Mike's Apple account). With one: `pkgbuild` with a postinstall that does what
     `install.command` does (it runs as root, so no password prompt), `productsign` with the
     "Developer ID Installer" certificate, `xcrun notarytool submit --wait`, `xcrun stapler
     staple`. Without one, ship the zip: macOS warns on the first open of `install.command`, and
     the README already says "right-click → Open".
9. **Premiere release build** (a branch + PR in `phantra-premiere-plugin`): package a `.ccx`
   with Adobe's UXP Developer Tool (Package), named `phantra-premiere-plugin-<version>.ccx`,
   version matching `manifest.json`. Note in its README how a `.ccx` installs (double-click with
   the Creative Cloud app; check Adobe's current docs before writing it down). Not uploaded yet.
10. **Upload script** (a branch + PR in this repo): `ops/upload_plugin_r2.py`, shaped like
    `ops/upload_mascot_r2.py`: `venv/bin/python -m ops.upload_plugin_r2 <file> --plugin
    resolve|premiere --version <v> [--write]`. It reports first (what would go up, and what is
    already there); `--write` uploads to `site/downloads/<plugin>/<version>/<file name>` through
    `src.storage`, and writes `site/downloads/<plugin>/<version>/SHA256SUMS`. It **refuses to
    overwrite** any key that already exists (a new build is a new version, never a replacement),
    and refuses a file whose name doesn't carry the version. Tests in `tests/` with the bucket
    patched (the suite blocks network).
11. **Upload the Resolve build (ask: the report first, then `--write` only on Mike's yes).**
    Check the public address answers: `curl -sI https://media.phantra.ai/site/downloads/resolve/<v>/<file>`
    shows 200 and the right `content-length`, and its sha256 matches the build's.
12. **The download page** (same PR as 10, or its own): `web/src/app/download/page.tsx` at
    `phantra.ai/download`, in the site's existing look (`areas/landing_page`: build on the site,
    never replace it). For each panel: what it does (from its README), "Requires DaVinci
    Resolve **Studio** 19.0.2+ on macOS", the version, the file size and its sha256, the Download
    button (the `site/downloads/...` address), the three install steps, how to sign in (the
    code at `/studio/link`), and a link to the license. Premiere shows "Coming soon" with no
    link until step 9's build has been run in Premiere. Add the page to `sitemap.ts`. In
    `web/src/components/studio/plugins-flyout.tsx`, give the DaVinci Resolve row
    `href: "/download"` (it is listed as not yet live today). `cd web && npm run typecheck &&
    node --test tests/*.test.mjs && npm run build` before the push; then open the built page in
    a browser and click the download.
13. **Docs:** `CLAUDE.md` gains one line under "The plugins": the panels are private repos and
    ship from `phantra.ai/download` (files under `site/downloads/` in the media bucket). The
    panels' READMEs say where to download.
14. **Report to Mike:** the build's sha256, the public download address, the page's PR and
    preview link, and whatever is still open (the `.pkg` if there's no Developer ID yet;
    Premiere until it has been run in Premiere; an Adobe Exchange listing, later).
