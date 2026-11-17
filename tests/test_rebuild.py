import asyncio
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from lab.pipeline import Budget, parse_scores, routed_ask, run
from lab.providers import MockProvider, ProviderError
from lab.router import SwarmRouter, limit_reset
from lab.store import Store
from lab.swarm_scout import candidates, promotion_seats, scout


class LimitedProvider(MockProvider):
    async def _call(self, system, prompt, kind):
        raise ProviderError("HTTP 429; retry after 2m15s")


class RouterTests(unittest.IsolatedAsyncioTestCase):
    def test_reset_formats(self):
        now = datetime(2026, 11, 17, tzinfo=timezone.utc).timestamp()
        self.assertIsNone(limit_reset("model timed out", now))
        self.assertEqual(limit_reset("quota exhausted", now), now + 300)
        self.assertEqual(limit_reset("rate limit; resets in 2m15s", now), now + 135)
        self.assertEqual(limit_reset('429 {"retry_after": 10}', now), now + 10)
        self.assertEqual(limit_reset("usage limit; resets at 2026-11-17T00:05:00Z", now), now + 300)
        self.assertEqual(limit_reset("429; Retry-After: Tue, 17 Nov 2026 00:05:00 GMT", now), now + 300)

    async def test_failover_and_reentry(self):
        primary, standby = LimitedProvider("claude", {}), MockProvider("codex", {})
        router = SwarmRouter()
        budget = Budget(5, 10_000)
        with patch("lab.router.time.time", return_value=100), self.assertLogs(level="WARNING"):
            _, used = await routed_ask(None, budget, [primary, standby], router, primary, 0,
                                       "ping", "test", record=False)
            self.assertIs(used, standby)
            self.assertEqual(router.cooldown_until["claude"], 235)
            self.assertFalse(router.active(primary))
        with patch("lab.router.time.time", return_value=235):
            self.assertTrue(router.active(primary))


class ScoreTests(unittest.TestCase):
    def test_gap_is_signed_integer_and_fields_are_mandatory(self):
        verdict = dict(novelty=2, testability=3, mechanism=4, survives_known_data=5,
                       gap_orders=-2, loophole_class="A", judge_model="test")
        self.assertEqual(parse_scores(json.dumps(verdict))["gap_orders"], -2)
        for invalid in ("-2", True, -2.5, None, 2**64):
            self.assertIsNone(parse_scores(json.dumps({**verdict, "gap_orders": invalid})))
        del verdict["judge_model"]
        self.assertIsNone(parse_scores(json.dumps(verdict)))


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_migration_wal_dedup_and_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lab.sqlite"
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE seats (id INTEGER PRIMARY KEY, sense TEXT, portal TEXT, role TEXT,"
                         " proposer TEXT, status TEXT, score REAL, verdict TEXT, error TEXT)")
            conn.execute("INSERT INTO seats (id, status, score) VALUES (7, 'done', 5)")
            conn.commit()
            conn.close()
            store, other = Store(path), Store(path)
            try:
                for connection in (store, other):
                    self.assertEqual(connection.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                    self.assertEqual(connection.db.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
                self.assertIsNone(store.seat(7)["gap_orders"])
                self.assertGreaterEqual(len(set(candidates(7))), 1000)
                labs = [MockProvider("gemini", {})]
                self.assertEqual(await scout(store, labs, 12, 2, 7, Budget(20, 10_000)), (12, 0))
                row = other.promotion_candidates(1, 1_000_000)[0]
                self.assertEqual(other.save_scout(row["visual_system"], row["loophole_class"],
                                                  row["amplifier"], "duplicate", 100), 0)
                pick = promotion_seats(store, 3)
                self.assertEqual((await run(pick, labs, store, Budget(20, 10_000), 2))["done"], 3)
                self.assertEqual(store.db.execute("SELECT count(*) FROM judge_scores").fetchone()[0], 3)
                self.assertTrue({s.id for s in pick}.isdisjoint(s.id for s in promotion_seats(store, 12)))
            finally:
                store.db.close()
                other.db.close()
