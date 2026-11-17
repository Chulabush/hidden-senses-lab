"""Manual Gemini Chat exchange. No Gemini executable, credentials, or API calls."""
import hashlib
import json
from pathlib import Path

from .agenda import Seat
from .pipeline import LOOPS
from .providers import Reply

SEED_OFFSET = 2_000_000


def export_packet(store, path, top=10):
    lines = ["# Gemini Chat architectural review", "",
             "Review these speculative dark-sector biological sensors. Distinguish established physics, "
             "conditional benchmarks, and conjecture. Do not assume biological coherence or amplification "
             "without a noise budget. Pivot naive individual-particle WIMP gravity.", "",
             *[f"- Loop {k}: {v}" for k, v in LOOPS.items()], "",
             "## Highest normalized quality scores"]
    rows = store.top(top)
    for row in rows:
        lines += [f"### Seat {row['id']}: quality={row['score']/10:.3f}; "
                  f"gap_orders={row['gap_orders']}; loop={row['loophole_class']}",
                  row['sense'], row['portal'], store.message(row['id'], 'revise'),
                  f"Judge/bottleneck: {row['verdict']}", ""]
    lines += ["## Lowest recorded gaps (conditional estimates; compare assumptions)"]
    for row in store.db.execute("SELECT id,gap_orders,verdict FROM seats WHERE status='done' "
                                "AND gap_orders IS NOT NULL ORDER BY gap_orders,id LIMIT ?", (top,)):
        lines += [f"- Seat {row['id']}: gap={row['gap_orders']}; {row['verdict']}"]
    lines += ["", "## Open biophysical bottlenecks",
              "Quantify coupling allowed by existing bounds, receptor transduction, thermal/shot noise, "
              "coherence time, integration bandwidth, and ordinary optical/magnetic backgrounds. "
              "Identify a cheap falsification experiment with sham controls.", "",
              "Return JSON only with this shape (new hypotheses become high-priority debate seeds):",
              '```json\n{"synthesis":"architectural review", "hypotheses":[{"hypothesis":'
              '"mechanism, finite benchmark, bottleneck and null test", "loophole_class":"B", '
              '"visual_system":"songbird retina"}]}\n```']
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    return path


def clipboard_text():
    import tkinter
    root = tkinter.Tk()
    root.withdraw()
    try:
        return root.clipboard_get()
    finally:
        root.destroy()


def import_packet(store, text):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get('synthesis'), str):
        raise ValueError('Expected synthesis string and hypotheses array; see gemini-export packet.')
    hypotheses = data.get('hypotheses', [])
    if not isinstance(hypotheses, list):
        raise ValueError('hypotheses must be an array')
    seeds = []
    for item in hypotheses:
        if (not isinstance(item, dict) or item.get('loophole_class') not in LOOPS
                or not all(isinstance(item.get(k), str) and item[k].strip()
                           for k in ('hypothesis', 'visual_system'))):
            raise ValueError('Each hypothesis needs hypothesis, visual_system and loophole_class A/B/C/D')
        seeds.append(item)
    digest = hashlib.sha256(text.encode()).hexdigest()
    with store.db:
        result = store.db.execute('INSERT OR IGNORE INTO gemini_imports (digest,synthesis) VALUES (?,?)',
                                  (digest, data['synthesis']))
        if not result.rowcount:
            return 0
        for item in seeds:
            store.db.execute('INSERT INTO gemini_seeds (hypothesis,visual_system,loophole_class) VALUES (?,?,?)',
                             (item['hypothesis'], item['visual_system'], item['loophole_class']))
    store.add_message(0, 'gemini:synthesis', 'gemini', Reply(data['synthesis'], 0, 0, 'Gemini Chat (manual)'))
    return len(seeds)


def pending_seats(store):
    return [Seat(SEED_OFFSET + row['id'], row['visual_system'],
                 f"Loop {row['loophole_class']}: {LOOPS[row['loophole_class']]}",
                 f"High-priority Gemini Chat seed: {row['hypothesis']}")
            for row in store.db.execute('SELECT g.* FROM gemini_seeds g LEFT JOIN seats s ON s.id=g.id+? '
                                       "WHERE s.status IS NULL OR s.status IN ('pending','failed') ORDER BY g.id",
                                       (SEED_OFFSET,))]
