# A photo attached in ChatGPT becomes an element

2026-11-05. Mike: "i want to be able to add references in the chat for phantra."

## The problem

A tool takes text. Until now a photo the person attached in a ChatGPT
conversation could reach Phantra only by a detour: `upload_link` minted a
one-time page, the person opened it and picked the same file again.

## What ChatGPT offers

The Apps SDK reference: a tool lists file-carrying top-level fields in
`_meta["openai/fileParams"]`. Each such field must resolve to a file object
(or an array of them) with `download_url` and `file_id` required and
`mime_type` and `file_name` declared as optional. ChatGPT always sends the
first two and may omit the others. The download address is temporary.

## As built

- `add_attached_photo(kind, name, file, notes)` in `src/mcp_server.py`, on
  the render listing (`LISTED_TOOLS`, right after `add_element`) only.
  Registered with `meta={"openai/fileParams": ["file"]}`; `_reg` now takes
  extra meta and merges it with the card's.
- `file`'s schema is written inline (`ATTACHED_FILE_SCHEMA`), not through a
  pydantic model, because pydantic puts a nested model under `$defs` and
  `tests/test_mcp_listed_review.py` screens every published key and value for
  a `$` (the "no selling" check). The optional fields carry no nullable
  branch.
- The body is `add_element` with a `picture` callable standing in for
  `source`, called where `_picture` would be: after the kind, the name and
  the Elements page's gate, so a refused caller fetches nothing. The
  callable fetches `download_url` through `refbin.fetch_public_image`
  (https at every hop, public hosts only, 15 MB), and `add_element` then
  decodes it and files it through the same create body. A `mime_type` that
  is not an image is refused before any fetch. The address is never stored.
- `add_element`'s render-listing description points a chat attachment at
  the new tool.

## Not done, on purpose

- The Claude listing: Claude hands a connector no attachments, so the tool
  would be a lie there. `upload_link` stays the way in. An agent with a
  shell (Claude Code, a desktop session with files) can already post the
  file to the `upload_link` page itself.
- The studio surface has `import_file`.
- Arrays of files: one photo per call, like `add_element`.

## To check after deploy

ChatGPT, signed in through the connector: attach a photo, ask to add it as a
character, and confirm the element appears with the photo. The listing's
tool set changed (43 tools), so OpenAI's scan sees a new tool on the next
review.
