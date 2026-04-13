"""프롬프트 YAML 저장소.

prompts.yaml 파일을 읽고 쓰며, Core 서비스에서도 동일 파일을 읽어
하드코딩 대신 사용할 수 있도록 한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


_DEFAULT_PROMPTS: dict[str, dict[str, str]] = {
    "base_system": {
        "name": "Base System Prompt",
        "description": "모든 대화에 적용되는 JARVIS 기본 시스템 프롬프트",
        "content": "You are JARVIS — an intelligent AI assistant system.",
    },
    "deepthink_planning": {
        "name": "Deep Think Planning",
        "description": "딥씽킹 플래닝 단계 프롬프트",
        "content": "You are JARVIS deep-thinking planning engine.",
    },
    "deepthink_execution": {
        "name": "Deep Think Execution",
        "description": "딥씽킹 실행 단계 프롬프트",
        "content": "You are JARVIS deep-thinking execution engine.",
    },
    "deepthink_summarize": {
        "name": "Deep Think Summarize",
        "description": "검색 결과 요약 프롬프트",
        "content": "You are JARVIS. Summarize the search results concisely.",
    },
}


class PromptStore:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path

    def load(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return self._default_envelope()

        with self.config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        if "prompts" not in data:
            data["prompts"] = dict(_DEFAULT_PROMPTS)
        return data

    def load_prompt(self, key: str) -> str | None:
        """특정 프롬프트의 content만 반환한다."""
        data = self.load()
        prompt = data.get("prompts", {}).get(key)
        if prompt is None:
            return None
        return prompt.get("content")

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["updated_at"] = self._now_iso()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                payload,
                f,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
        return payload

    def update_prompt(self, key: str, content: str) -> dict[str, Any]:
        """특정 프롬프트만 업데이트한다."""
        data = self.load()
        if key not in data.get("prompts", {}):
            data.setdefault("prompts", {})[key] = {
                "name": key,
                "description": "",
                "content": content,
            }
        else:
            data["prompts"][key]["content"] = content
        return self.save(data)

    def _default_envelope(self) -> dict[str, Any]:
        return {
            "version": 1,
            "updated_at": self._now_iso(),
            "prompts": dict(_DEFAULT_PROMPTS),
        }

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def load_prompt_from_yaml(config_path: Path, key: str) -> str | None:
    """Core 서비스용: prompts.yaml에서 특정 프롬프트 content를 읽는 유틸 함수."""
    store = PromptStore(config_path)
    return store.load_prompt(key)
