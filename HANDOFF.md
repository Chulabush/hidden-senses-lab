# Windows rebuild hand-off

Verified on 2026-11-17 in `C:\Projects\hidden-senses-lab`.

- Claude and Codex both returned `ready` in live subscription CLI pings.
- Gemini is a manual Chat Bridge, excluded from automated provider construction and doctor pings.
  No Gemini CLI installation or API key is needed for `lab.cli.toml`.
- Full executable paths resolve through `shutil.which`; Windows npm shims are translated to
  native Claude / Node Codex entry points without a shell.
- Existing cooldown routing, personas, one-call screening, signed integer gap validation,
  normalized ranking and WAL migration were retained. Synthesis now also uses cooldown routing.
- Scout task concurrency respects the two-process CLI cap. The existing 1,248-combination
  matrix supports resumable selection of 1,000 candidates and top-candidate promotion.
- Gemini imports store synthesis and high-priority seeds, validate the whole packet before
  writes, deduplicate identical packets, and feed seeds into the next debate run.

## Local checks

Six unit/integration tests pass, including a fresh 1,000-candidate mock scout, migration,
two-connection WAL/busy-timeout settings, score validation, cooldown failover/re-entry,
bridge validation/deduplication/priority, and debate promotion.
Three additional mock promotions completed with no failed or rejected seats.
Production SQLite integrity check: `ok`; journal mode: `wal`.
Consistent SQLite backup: `runs/lab.sqlite.bak` (65,536 bytes).
Generated real-data packet: `runs/gemini_brief.md`.

Python was absent from PATH. A Python 3.13.9 embedded runtime was downloaded from python.org
to ignored `.runtime/python`; use `.runtime/python/python.exe` instead of `py` on this laptop.
Windows clipboard imports use the native API and do not require tkinter.

## Next commands

```powershell
.runtime/python/python.exe -m lab --config lab.cli.toml gemini-export --top 10
# Paste runs/gemini_brief.md into Gemini Chat, then save its JSON response:
.runtime/python/python.exe -m lab --config lab.cli.toml gemini-import runs/gemini_reply.json
.runtime/python/python.exe -m lab --config lab.cli.toml run --seats 6
.runtime/python/python.exe -m lab --config lab.cli.toml scout --count 1000 --concurrency 2 --promote-top 3
.runtime/python/python.exe -m lab --config lab.cli.toml status
```

The request ended at the Scout Matrix heading; the existing resumable matrix was used as
the implementation scope. No 1,000-call live research batch was executed. Live verification
used tiny login pings; research correctness and frontier coupling feasibility remain unproven.
The four loops are speculative research prompts, not evidence of biological dark-matter sensing.
Existing scored seats were preserved rather than silently rescored. Legacy gaps may be absent;
new mandatory judge data lives in `judge_scores` with per-seat gap/class summaries.
Cooldowns last for the current process; both unavailable workers pause work for a later rerun.
No actual Gemini response was available, so import was validated with synthetic packets.
