"""Shared structured action logger.

Every major pipeline action appends one JSON line to logs/actions.jsonl:
timestamp, phase, action, inputs, outputs, status. Required by the project's
operating rules; consumed when assembling the report's methodology section.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTIONS_PATH = PROJECT_ROOT / "logs" / "actions.jsonl"

_lock = threading.Lock()


def log_action(
    phase: str,
    action: str,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    status: str = "ok",
) -> None:
    """Append one structured action record. Never raises (logging must not kill a fetch)."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "action": action,
        "inputs": inputs or {},
        "outputs": outputs or {},
        "status": status,
    }
    try:
        ACTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _lock, open(ACTIONS_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
