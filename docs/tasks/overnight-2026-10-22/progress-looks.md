# Progress: group 2, free looks (branch `claude/overnight-looks`)

A ticked copy of the group's checkboxes in `docs/tasks/task-overnight-2026-10-22.md`.

- [x] The five looks (`film_grade`, `noir`, `flash_2000s`, `crash_zoom`, `vertical_ready`) as a
      no-provider kind in the effects table, 0 credits, through `POST /api/effects/run`;
      `tests/test_looks.py` on synthetic `testsrc2` fixtures; processing time per second logged.
- [x] Objective checks: Noir U/V within ±2 of 128; Vertical Ready width/height == 9/16 exactly;
      Film Grade active picture 2.39:1 ±0.01; Crash-Zoom frame at 0.3s zoomed >= 1.15; timing logged.
- [x] `make_it_pro` bundle: Film Grade -> Vertical Ready free, Sound Pass as a priced card only;
      test: zero ledger holds, Sound Pass yields a quote instead of running.
- [x] "Made in Phantra" end card (1s) as `looks.append_end_card`; test: duration = input + 1s, last
      second differs from the input's last frame.
- [ ] Contact sheet at `docs/qa/looks-contact-sheet.png` (synthetic fixtures; real clips need Mike's yes).
