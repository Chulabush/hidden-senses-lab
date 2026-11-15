"""Load lab.toml and an optional .env file."""
import os
import tomllib
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if value.strip():
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def load(path: str) -> dict:
    cfg_path = Path(path)
    load_env(cfg_path.parent / ".env")
    cfg = tomllib.loads(cfg_path.read_text())
    cfg["_root"] = cfg_path.parent
    if not cfg.get("providers"):
        raise SystemExit(f"{path}: no [providers.*] sections")
    return cfg
