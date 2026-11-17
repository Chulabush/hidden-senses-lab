"""SQLite blackboard: every message the labs exchange, plus scores and usage."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS gemini_imports (
  digest TEXT PRIMARY KEY, synthesis TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS gemini_seeds (
  id INTEGER PRIMARY KEY, hypothesis TEXT NOT NULL, visual_system TEXT NOT NULL,
  loophole_class TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 100);
CREATE TABLE IF NOT EXISTS seats (
  id INTEGER PRIMARY KEY, sense TEXT, portal TEXT, role TEXT,
  proposer TEXT, status TEXT DEFAULT 'pending', score REAL, verdict TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, seat_id INTEGER, step TEXT, provider TEXT, model TEXT,
  content TEXT, in_tokens INTEGER, out_tokens INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS messages_seat ON messages(seat_id);
CREATE TABLE IF NOT EXISTS judge_scores (
  message_id INTEGER PRIMARY KEY, seat_id INTEGER NOT NULL, provider TEXT NOT NULL,
  judge_model TEXT NOT NULL, gap_orders INTEGER, loophole_class TEXT,
  novelty INTEGER NOT NULL, testability INTEGER NOT NULL, mechanism INTEGER NOT NULL,
  survives_known_data INTEGER NOT NULL, normalized_score REAL NOT NULL);
CREATE TABLE IF NOT EXISTS scout_candidates (
  id INTEGER PRIMARY KEY, visual_system TEXT NOT NULL, loophole_class TEXT NOT NULL,
  amplifier TEXT NOT NULL, hypothesis TEXT NOT NULL, potential INTEGER NOT NULL,
  UNIQUE(visual_system, loophole_class, amplifier));
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            columns = {row["name"] for row in self.db.execute("PRAGMA table_info(seats)")}
            if "gap_orders" not in columns:
                self.db.execute("ALTER TABLE seats ADD COLUMN gap_orders INTEGER")
            if "loophole_class" not in columns:
                self.db.execute("ALTER TABLE seats ADD COLUMN loophole_class TEXT")

    def done_ids(self) -> set[int]:
        return {r["id"] for r in self.db.execute("SELECT id FROM seats WHERE status IN ('done', 'rejected')")}

    def start_seat(self, seat, proposer: str) -> None:
        # A seat that was interrupted starts over, so drop its partial transcript.
        self.db.execute("DELETE FROM judge_scores WHERE seat_id=?", (seat.id,))
        self.db.execute("DELETE FROM messages WHERE seat_id=?", (seat.id,))
        self.db.execute(
            "INSERT OR REPLACE INTO seats (id, sense, portal, role, proposer, status) VALUES (?,?,?,?,?, 'running')",
            (seat.id, seat.sense, seat.portal, seat.role, proposer),
        )
        self.db.commit()

    def set_proposer(self, seat_id, proposer):
        with self.db:
            self.db.execute("UPDATE seats SET proposer=? WHERE id=?", (proposer, seat_id))

    def save_verdicts(self, seat_id, verdicts, keys):
        with self.db:
            self.db.execute("DELETE FROM judge_scores WHERE seat_id=?", (seat_id,))
            values = []
            for message_id, provider, data in verdicts:
                axes = [data[k] for k in keys]
                values.append((message_id, seat_id, provider, data["judge_model"],
                               data["gap_orders"], data["loophole_class"], *axes, sum(axes) / 40))
            self.db.executemany("INSERT INTO judge_scores VALUES (?,?,?,?,?,?,?,?,?,?,?)", values)
            score = round(sum(v[-1] for v in values) / len(values) * 10, 2) if values else None
            gaps = [(d["gap_orders"], d["loophole_class"]) for _, _, d in verdicts if d["gap_orders"] is not None]
            gap, category = min(gaps, default=(None, None))
            note = " | ".join(d["one_line"] for _, _, d in verdicts) or "no parseable scores"
            self.db.execute(
                """UPDATE seats SET status='done', score=?, verdict=?, error=NULL,
                   gap_orders=?, loophole_class=? WHERE id=?""", (score, note, gap, category, seat_id))

    def scout_exists(self, visual, category, amplifier):
        return self.db.execute(
            "SELECT 1 FROM scout_candidates WHERE visual_system=? AND loophole_class=? AND amplifier=?",
            (visual, category, amplifier),
        ).fetchone() is not None

    def save_scout(self, visual, category, amplifier, hypothesis, potential):
        with self.db:
            result = self.db.execute(
                """INSERT INTO scout_candidates (visual_system, loophole_class, amplifier, hypothesis, potential)
                   VALUES (?,?,?,?,?) ON CONFLICT(visual_system, loophole_class, amplifier) DO NOTHING""",
                (visual, category, amplifier, hypothesis, potential),
            )
        return result.rowcount

    def promotion_candidates(self, count, id_offset):
        return self.db.execute(
            """SELECT c.* FROM scout_candidates c LEFT JOIN seats s ON s.id = c.id + ?
               WHERE s.status IS NULL OR s.status IN ('pending', 'failed')
               ORDER BY potential DESC, c.id LIMIT ?""",
            (id_offset, count),
        ).fetchall()

    def add_message(self, seat_id: int, step: str, provider: str, reply) -> None:
        self.db.execute(
            "INSERT INTO messages (seat_id, step, provider, model, content, in_tokens, out_tokens) VALUES (?,?,?,?,?,?,?)",
            (seat_id, step, provider, reply.model, reply.text, reply.in_tokens, reply.out_tokens),
        )
        self.db.commit()

    def finish_seat(self, seat_id: int, status: str, score=None, verdict=None, error=None) -> None:
        self.db.execute(
            "UPDATE seats SET status=?, score=?, verdict=?, error=? WHERE id=?",
            (status, score, verdict, error, seat_id),
        )
        self.db.commit()

    def clear_synthesis(self) -> None:
        self.db.execute("DELETE FROM messages WHERE seat_id=0")
        self.db.commit()

    def top(self, k: int):
        return self.db.execute(
            "SELECT * FROM seats WHERE status='done' AND score IS NOT NULL ORDER BY score DESC, gap_orders IS NULL, gap_orders, id LIMIT ?", (k,)
        ).fetchall()

    def message(self, seat_id: int, step: str) -> str:
        row = self.db.execute(
            "SELECT content FROM messages WHERE seat_id=? AND step=? ORDER BY id DESC LIMIT 1", (seat_id, step)
        ).fetchone()
        return row["content"] if row else ""

    def transcript(self, seat_id: int):
        return self.db.execute("SELECT * FROM messages WHERE seat_id=? ORDER BY id", (seat_id,)).fetchall()

    def seat(self, seat_id: int):
        return self.db.execute("SELECT * FROM seats WHERE id=?", (seat_id,)).fetchone()

    def status_counts(self):
        return self.db.execute("SELECT status, COUNT(*) n FROM seats GROUP BY status").fetchall()

    def usage(self):
        return self.db.execute(
            "SELECT provider, COUNT(*) calls, SUM(in_tokens) tin, SUM(out_tokens) tout FROM messages GROUP BY provider"
        ).fetchall()
