from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


class ConfigStore:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"version": 1, "updated_at": self._now_iso(), "services": {}}
        with self.config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if "services" not in data:
            data["services"] = {}
        return data

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["updated_at"] = self._now_iso()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)
        return payload

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
