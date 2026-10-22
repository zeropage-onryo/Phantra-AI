# Phantra

An AI production studio. Bring an idea and your own photos; get stills and video made on
current image and video models, held to those photos, and pay in credits only for what you
approve. Live at [phantra.ai](https://phantra.ai). (Named Zero Page until 2026-10-13.)

## What it does

- **Create.** One chat box. The assistant talks an idea through, proposes a plan, and makes a
  still or writes a scene when asked. Every step that costs credits waits on a card that
  shows the price.
- **Scenes held to your photos.** A scene is written as timed shots and rendered shot by shot
  against the photos of your characters, products and places. A scene with no photographs
  does not render.
- **Projects.** A brief, a look and a memory per piece of work.
- **Library and effects.** Everything you made, with image edits, camera moves, upscaling,
  sound, reframing, draft-then-finish and real downloads.
- **Editor.** A timeline over your rendered clips, with an agent that proposes edits you keep
  or undo, and export to MP4, audio, a still or OpenTimelineIO.
- **Connector.** An MCP server so Claude or ChatGPT can work in your workspace:
  `https://api.phantra.ai/mcp` and `https://api.phantra.ai/mcp/claude`. See
  [phantra.ai/connector](https://phantra.ai/connector).

## How it is built

| Part | Where |
| --- | --- |
| Site and studio | Next.js in `web/`, on Vercel |
| API | FastAPI in `app/` over the library in `src/`, on Fly |
| Data and sign-in | Postgres and Auth on Supabase |
| Media | Cloudflare R2, served at media.phantra.ai |
| Video and image models | fal.ai (Kling, Veo, Seedance, LTX, Wan, FLUX and others) and Gemini |
| Billing | Stripe plans that grant credits; a ledger hold before every provider call |

## Running it

```bash
venv/bin/pip install -r requirements.txt
venv/bin/pip install -e .
venv/bin/uvicorn app.main:app --reload      # the API on 127.0.0.1:8000
cd web && npm install && npm run dev        # the studio on localhost:3000
```

`.env.example` and `web/.env.example` list the settings. `START_SERVER.md` covers the local
server and the MCP mount; `CLAUDE.md` is the working guide to the code, commands and
conventions; `docs/` holds the task files, the billing design and the runbook.

## Checks

```bash
venv/bin/python -m pytest tests/ -q
venv/bin/ruff check .
cd web && node --test tests/*.test.mjs && npm run typecheck && npm run build
```

The test suite blocks all network access, so a test cannot make a billed call.

The README this replaced is kept at `docs/retired/README-before-phantra.md`.
