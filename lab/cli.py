"""Command line: doctor, plan, run, synthesize, status, show."""
import argparse
import asyncio
import sys
from pathlib import Path

from . import agenda, config, pipeline, providers
from .store import Store

CALLS_PER_SEAT = 6  # propose + 2 critiques + revise + 2 scores


def open_store(cfg, mock: bool) -> Store:
    path = cfg["_root"] / cfg["run"].get("db", "runs/lab.sqlite")
    return Store(path.with_name("mock.sqlite") if mock else path)


def chosen(cfg, args, mock: bool = False) -> list:
    """The configured labs, narrowed by --labs if given."""
    labs = providers.build(cfg, mock)
    if args.labs:
        want = [n.strip() for n in args.labs.split(",") if n.strip()]
        unknown = [n for n in want if n not in {p.name for p in labs}]
        if unknown:
            raise SystemExit(f"--labs: no such lab {', '.join(unknown)} (configured: {', '.join(p.name for p in labs)})")
        labs = [p for p in labs if p.name in want]
    return labs


def ready(cfg, args) -> list:
    labs = []
    for p in chosen(cfg, args, args.mock):
        reason = p.missing()
        if reason:
            print(f"  skipping {p.name}: {reason}")
        else:
            labs.append(p)
    if not labs:
        raise SystemExit("No lab is ready. Add keys to .env (see .env.example), or try the pipeline with --mock.")
    print("  labs in this run: " + ", ".join(f"{p.name} ({p.model or p.kind})" for p in labs))
    return labs


def budget(cfg) -> pipeline.Budget:
    run = cfg["run"]
    return pipeline.Budget(int(run.get("max_calls", 600)), int(run.get("max_output_tokens", 3_000_000)))


def cmd_doctor(cfg, args):
    async def check(p):
        reason = p.missing()
        if reason:
            return f"{p.name:8} NOT READY  {reason}"
        line = f"{p.name:8} ready      model={p.model or '-'}"
        try:
            models = await p.list_models()
        except Exception as e:  # doctor reports whatever went wrong rather than stopping
            return line + f"\n         could not list models: {e}"
        if models:
            known = "available" if p.model in models else "NOT in your account's model list"
            line += f" ({known})\n         models: {', '.join(sorted(models)[:40])}"
        if args.ping:
            try:
                reply = await asyncio.wait_for(p.complete("Reply with the single word: ready", "ping", "ping"), 90)
                line += f"\n         ping ok: {reply.text.strip()[:40]!r}"
            except asyncio.TimeoutError:
                line += "\n         ping FAILED: no reply in 90 seconds (not logged in, or no network?)"
            except providers.ProviderError as e:
                line += f"\n         ping FAILED: {e}"
        return line

    async def go():
        for line in await asyncio.gather(*(check(p) for p in chosen(cfg, args))):
            print(line)

    asyncio.run(go())


def cmd_plan(cfg, args):
    total = len(agenda.all_seats())
    n = min(args.seats or total, total)
    labs = len(cfg["providers"])
    print(f"Agenda: {len(agenda.SENSES)} senses x {len(agenda.PORTALS)} portals x {len(agenda.ROLES)} disciplines"
          f" = {total} agent seats")
    print(f"This plan: {n} seats -> about {n * CALLS_PER_SEAT} model calls, ~{n * CALLS_PER_SEAT // labs} per lab")
    print(f"Limits per run: {cfg['run'].get('max_calls')} calls, {cfg['run'].get('max_output_tokens'):,} output tokens"
          f" (edit [run] in lab.toml)")


def cmd_run(cfg, args):
    store = open_store(cfg, args.mock)
    labs = ready(cfg, args)
    done = store.done_ids()
    seats = [s for s in agenda.sample(args.seats, int(cfg["run"].get("seed", 7))) if s.id not in done]
    if not seats:
        print("All requested seats are already done. Raise --seats to go further.")
        return
    b = budget(cfg)
    print(f"  working {len(seats)} seats ({len(done)} already done)")
    stats = asyncio.run(pipeline.run(seats, labs, store, b, int(cfg["run"].get("concurrency", 12))))
    print(f"Finished: {stats['done']} seats done, {stats['failed']} failed, {b.calls} calls, {b.out:,} output tokens.")
    if stats["streak"] >= pipeline.MAX_FAILURE_STREAK:
        print("Stopped after repeated failures (see above): usually a usage limit or a logged-out tool."
              " Run again later; finished seats are kept and failed ones are retried.")
    elif stats["stopped"]:
        print("Stopped at the budget limit in the config. Run again to continue where it left off.")


def cmd_synthesize(cfg, args):
    store = open_store(cfg, args.mock)
    labs = ready(cfg, args)
    text = asyncio.run(pipeline.synthesize(labs, cfg["run"].get("lead", ""), store, budget(cfg), args.top))
    lines = ["# Hidden Senses Lab: research programme", "", text, "", "## Top hypotheses", "",
             "| Seat | Score | Proposed by | Sense | Link to the unseen |", "|---|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['score']} | {r['proposer']} | {r['sense']} | {r['portal']} |" for r in store.top(args.top)]
    lines += ["", "## Usage", "", "| Lab | Calls | Input tokens | Output tokens |", "|---|---|---|---|"]
    lines += [f"| {u['provider']} | {u['calls']} | {u['tin']:,} | {u['tout']:,} |" for u in store.usage()]
    out = Path(store.db.execute("PRAGMA database_list").fetchone()[2]).with_name(
        "mock-report.md" if args.mock else "report.md")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


def cmd_status(cfg, args):
    store = open_store(cfg, args.mock)
    for r in store.status_counts():
        print(f"{r['status']:8} {r['n']}")
    for u in store.usage():
        print(f"{u['provider']:8} {u['calls']} calls, {u['tin']:,} in / {u['tout']:,} out tokens")
    for r in store.top(args.top):
        print(f"  seat {r['id']:5} score {r['score']:5}  {r['sense'].split(':')[0]}  x  {r['portal'].split(':')[0][:60]}")


def cmd_show(cfg, args):
    store = open_store(cfg, args.mock)
    seat = store.seat(args.seat)
    if not seat:
        raise SystemExit(f"Seat {args.seat} has not been worked yet.")
    print(f"Seat {seat['id']} [{seat['status']}] score={seat['score']}\n{seat['sense']}\n{seat['portal']}\n{seat['role']}")
    for m in store.transcript(args.seat):
        print(f"\n--- {m['step']} · {m['provider']} ({m['model']}) ---\n{m['content']}")


def cmd_consult(cfg, args):
    store = open_store(cfg, args.mock)
    if not args.source:
        print(pipeline.consult_prompt(store, args.seat))
        return
    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    if not text.strip():
        raise SystemExit("The reply is empty.")
    reply = providers.Reply(text.strip(), 0, len(text) // 4, f"{args.source} (pasted from chat)")
    store.add_message(args.seat, f"consult:{args.source}", args.source, reply)
    if args.seat == 0:
        report = Path(store.db.execute("PRAGMA database_list").fetchone()[2]).with_name("report.md")
        if report.exists():
            with report.open("a", encoding="utf-8") as f:
                f.write(f"\n## Outside review from {args.source}\n\n{text.strip()}\n")
        print(f"Saved {args.source}'s review of the research programme.")
    else:
        pipeline.rescore(store, args.seat)
        print(f"Saved {args.source}'s review of seat {args.seat}; seat score is now {store.seat(args.seat)['score']}.")


def main():
    ap = argparse.ArgumentParser(prog="lab", description="Hidden Senses Lab: Claude, ChatGPT and Gemini as one research group")
    ap.add_argument("--config", default="lab.toml")
    ap.add_argument("--labs", help="use only these labs, comma-separated, e.g. claude,gemini")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor", help="check keys and list the models each key can use")
    d.add_argument("--ping", action="store_true", help="also send one tiny request to each lab")
    p = sub.add_parser("plan", help="show the size of the agenda and of a run")
    p.add_argument("--seats", type=int)
    r = sub.add_parser("run", help="work research seats (resumes where it stopped)")
    r.add_argument("--seats", type=int, default=30)
    s = sub.add_parser("synthesize", help="turn the best hypotheses into a research programme")
    t = sub.add_parser("status", help="progress, usage and current leaders")
    w = sub.add_parser("show", help="print the full conversation for one seat")
    w.add_argument("seat", type=int)
    c = sub.add_parser("consult", help="get an outside opinion from a chat window (ChatGPT, Gemini, ...)")
    c.add_argument("seat", type=int, help="seat number, or 0 for the research programme")
    c.add_argument("--from", dest="source", help="who answered, e.g. chatgpt; omit to print the prompt to paste")
    c.add_argument("--file", help="file holding the pasted reply (default: read it from standard input)")
    for q in (s, t):
        q.add_argument("--top", type=int, default=30)
    for q in (r, s, t, w, c):
        q.add_argument("--mock", action="store_true", help="offline simulation, no keys, no cost")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):  # model output is full of symbols a Windows console cannot encode
        stream.reconfigure(encoding="utf-8", errors="replace")
    cfg = config.load(args.config)
    {"doctor": cmd_doctor, "plan": cmd_plan, "run": cmd_run, "synthesize": cmd_synthesize,
     "status": cmd_status, "show": cmd_show, "consult": cmd_consult}[args.cmd](cfg, args)
