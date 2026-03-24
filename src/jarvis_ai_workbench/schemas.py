from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConfigEnvelope(BaseModel):
    version: int = 1
    updated_at: str
    services: dict[str, dict[str, Any]] = Field(default_factory=dict)
