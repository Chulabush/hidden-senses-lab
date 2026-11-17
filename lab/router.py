"""Route around limited or unavailable providers within one run."""
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

ROLES = {
    "gemini": "Cross-Domain Evolutionary & Cosmological Synthesizer. Connect comparative visual anatomy to dark-sector models.",
    "claude": "Molecular & Neuro-Optical Biophysical Engineer. Trace receptor-to-optic-nerve transduction.",
    "codex": "Quantum Signal-to-Noise & Falsification Modeler. Estimate thresholds and coherence times and specify controls.",
}
ROLES["chatgpt"] = ROLES["codex"]
LIMIT = re.compile(r"\b429\b|rate.limit|usage.limit|too many requests|resource_exhausted|quota|hit your limit|capacity exhausted", re.I)
RESET = re.compile(r"\b(?:reset(?:s|_at|_time)?|retry[-_ ]after)\b[\"']?\s*(?:[:=]|at\s+|in\s+)?\s*[\"']?([^\n,}\"']+)", re.I)


def limit_reset(message, now):
    if not LIMIT.search(message):
        return None
    for match in RESET.finditer(message):
        value = match[1].strip()
        iso = re.match(r"\d{4}-\d\d-\d\d[T ]\d\d:\d\d(?::\d\d(?:\.\d+)?)?(?:Z|[+-]\d\d:\d\d)?", value)
        if iso:
            try:
                return max(now + 1, datetime.fromisoformat(iso[0].replace("Z", "+00:00")).timestamp())
            except ValueError:
                continue
        clock = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)(?:\s*\(([^)]+)\))?", value, re.I)
        if clock:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

            try:
                local = datetime.fromtimestamp(now, ZoneInfo(clock[4]) if clock[4] else None)
                reset = local.replace(hour=int(clock[1]) % 12 + 12 * (clock[3].lower() == "pm"),
                                      minute=int(clock[2] or 0), second=0, microsecond=0)
                return (reset if reset.timestamp() > now else reset + timedelta(days=1)).timestamp()
            except (ValueError, ZoneInfoNotFoundError):
                continue
        durations = re.findall(r"(\d+(?:\.\d+)?)\s*(d(?:ays?)?|h(?:ours?|rs?)?|m(?:inutes?|ins?)?|s(?:econds?|ecs?)?)(?=\d|\b)", value, re.I)
        if durations:
            scale = {"d": 86400, "h": 3600, "m": 60, "s": 1}
            return now + max(1, sum(float(n) * scale[unit[0].lower()] for n, unit in durations))
        number = re.match(r"\d+(?:\.\d+)?(?=\s|$)", value)
        if number:
            n = float(number[0])
            if n >= 1e12:
                n /= 1000
            return max(now + 1, n if n >= 1e9 else now + n)
    http_date = re.search(r"retry[-_ ]after\s*[:=]\s*(\w{3}, [^\n]+? GMT)", message, re.I)
    if http_date:
        try:
            return max(now + 1, parsedate_to_datetime(http_date[1]).timestamp())
        except ValueError:
            pass
    return now + 300


class SwarmRouter:
    def __init__(self):
        self.cooldown_until = {}
        self.unavailable = set()

    def active(self, provider):
        return provider.name not in self.unavailable and time.time() >= self.cooldown_until.get(provider.name, 0)

    def failed(self, provider, error):
        now = time.time()
        deadline = limit_reset(str(error), now)
        if deadline is not None:
            deadline = max(deadline, self.cooldown_until.get(provider.name, 0))
            self.cooldown_until[provider.name] = deadline
            logging.warning("%s cooling down until %s", provider.name,
                            datetime.fromtimestamp(deadline, timezone.utc).isoformat())
        else:
            self.unavailable.add(provider.name)
            logging.warning("%s unavailable for this run: %s", provider.name, error)
