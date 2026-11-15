"""SQLite blackboard: every message the labs exchange, plus scores and usage."""
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS seats (
  id INTEGER PRIMARY KEY, sense TEXT, portal TEXT, role TEXT,
  proposer TEXT, status TEXT DEFAULT 'pending', score REAL, verdict TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, seat_id INTEGER, step TEXT, provider TEXT, model TEXT,
  content TEXT, in_tokens INTEGER, out_tokens INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS messages_seat ON messages(seat_id);
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def done_ids(self) -> set[int]:
        return {r["id"] for r in self.db.execute("SELECT id FROM seats WHERE status='done'")}

    def start_seat(self, seat, proposer: str) -> None:
        # A seat that was interrupted starts over, so drop its partial transcript.
        self.db.execute("DELETE FROM messages WHERE seat_id=?", (seat.id,))
        self.db.execute(
            "INSERT OR REPLACE INTO seats (id, sense, portal, role, proposer, status) VALUES (?,?,?,?,?, 'running')",
            (seat.id, seat.sense, seat.portal, seat.role, proposer),
        )
        self.db.commit()

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
            "SELECT * FROM seats WHERE status='done' AND score IS NOT NULL ORDER BY score DESC, id LIMIT ?", (k,)
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
