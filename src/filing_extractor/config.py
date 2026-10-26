"""Environment and path helpers. Secrets come from the environment or a git-ignored .env."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = ROOT / "raw"
OUTPUT_DIR = ROOT / "outputs"


def load_env(path: Path | None = None) -> None:
    """Read KEY=VALUE lines from .env into os.environ without overriding real variables."""
    env_file = path or ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def sec_user_agent() -> str:
    """SEC fair access needs a User-Agent with a name and an email address."""
    load_env()
    agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not agent or "@" not in agent or "example.com" in agent:
        raise RuntimeError(
            "Set SEC_USER_AGENT in .env to 'Your Name your.email@domain' (SEC fair access)."
        )
    return agent
