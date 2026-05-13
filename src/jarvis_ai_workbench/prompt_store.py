"""프롬프트 YAML 저장소.

prompts.yaml 파일을 읽고 쓰며, Core 서비스에서도 동일 파일을 읽어
하드코딩 대신 사용할 수 있도록 한다.
"""

from __future__ import annotations

import ast
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _default_prompt_from_python(
    relative_path: str,
    constant_name: str,
    fallback: str,
) -> str:
    source_path = Path(__file__).resolve().parents[3] / relative_path
    try:
        module = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in module.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == constant_name:
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str) and value.strip():
                        return value
    except Exception:
        pass

    return fallback


def _default_action_intent_gate_prompt() -> str:
    return (
        _default_prompt_from_python(
            "jarvis_controller/src/planner/action_gate.py",
            "_INTENT_GATE_PROMPT_FALLBACK",
            "You are JARVIS Action Intent Gate.\n"
            "Output only valid JSON. Do not answer the user. "
            "Decide whether the user asks JARVIS to operate the local computer.",
        )
    )


def _default_chat_base_prompt() -> str:
    return _default_prompt_from_python(
        "jarvis_core/src/application/chat/service.py",
        "_BASE_SYSTEM_PROMPT_FALLBACK",
        "You are JARVIS — an intelligent AI assistant system.",
    )


def _default_realtime_system_prompt() -> str:
    return _default_prompt_from_python(
        "jarvis_core/src/application/chat/service.py",
        "_REALTIME_COMPACT_SYSTEM_PROMPT",
        "너는 JARVIS. 한국어로 짧게 답해. 컴퓨터 조작 요청은 '진행하겠습니다!'만 출력.",
    )


def _default_deepthink_planning_prompt() -> str:
    return _default_prompt_from_python(
        "jarvis_core/src/application/deepthink/service.py",
        "_PLANNING_SYSTEM_PROMPT_FALLBACK",
        "You are JARVIS deep-thinking planning engine.",
    )


def _default_deepthink_execution_prompt() -> str:
    return _default_prompt_from_python(
        "jarvis_core/src/application/deepthink/service.py",
        "_EXECUTION_SYSTEM_PROMPT_FALLBACK",
        "You are JARVIS deep-thinking execution engine.",
    )


def _default_deepthink_summarize_prompt() -> str:
    return _default_prompt_from_python(
        "jarvis_core/src/application/deepthink/service.py",
        "_SUMMARIZE_SYSTEM_PROMPT_FALLBACK",
        "You are JARVIS. Summarize the search results concisely.",
    )


_DEFAULT_PROMPTS: dict[str, dict[str, str]] = {
    "base_system": {
        "name": "Base System Prompt",
        "description": "모든 대화에 적용되는 JARVIS 기본 시스템 프롬프트",
        "content": _default_chat_base_prompt(),
    },
    "realtime_system": {
        "name": "Realtime System Prompt",
        "description": "Ollama realtime/e2b 채팅에 적용되는 짧은 시스템 프롬프트",
        "content": _default_realtime_system_prompt(),
    },
    "deepthink_planning": {
        "name": "Deep Think Planning",
        "description": "딥씽킹 플래닝 단계 프롬프트",
        "content": _default_deepthink_planning_prompt(),
    },
    "deepthink_execution": {
        "name": "Deep Think Execution",
        "description": "딥씽킹 실행 단계 프롬프트",
        "content": _default_deepthink_execution_prompt(),
    },
    "deepthink_summarize": {
        "name": "Deep Think Summarize",
        "description": "검색 결과 요약 프롬프트",
        "content": _default_deepthink_summarize_prompt(),
    },
    "action_intent_gate": {
        "name": "Action Intent Gate Prompt",
        "description": (
            "사용자 발화를 로컬 컴퓨터 액션으로 실행할지 판단하는 "
            "인텐트 게이트 프롬프트"
        ),
        "content": _default_action_intent_gate_prompt(),
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

        prompts = data.setdefault("prompts", {})
        for key, prompt in _DEFAULT_PROMPTS.items():
            prompts.setdefault(key, deepcopy(prompt))
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
            "prompts": deepcopy(_DEFAULT_PROMPTS),
        }

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def load_prompt_from_yaml(config_path: Path, key: str) -> str | None:
    """Core 서비스용: prompts.yaml에서 특정 프롬프트 content를 읽는 유틸 함수."""
    store = PromptStore(config_path)
    return store.load_prompt(key)
