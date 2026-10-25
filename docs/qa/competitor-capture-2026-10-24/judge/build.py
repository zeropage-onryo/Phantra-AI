# ruff: noqa: E501, E702, E731  (a one-off QA data script, 2026-10-24)
# Inlines data.json into template.html -> blind-dailies.html, pointing each take at
# its bundled file clips/<brief><take>.mp4 (an artifact can't load video from other hosts).
import json
import pathlib

d = pathlib.Path(__file__).parent
data = json.loads((d / "data.json").read_text())
for b in data:
    for i, c in enumerate(b["clips"]):
        c["source_url"] = c.pop("url")
        c["url"] = f"clips/{b['id'].lower()}{i + 1}.mp4"
html = (d / "template.html").read_text().replace("/*DATA*/[]", json.dumps(data, ensure_ascii=False))
(d / "blind-dailies.html").write_text(html)
print("built", len(html))
