from pathlib import Path

from fastapi.testclient import TestClient

from jarvis_ai_workbench.app import create_app
from jarvis_ai_workbench.prompt_store import PromptStore


def make_client(tmp_path: Path) -> TestClient:
    config_path = tmp_path / "ai.yaml"
    app = create_app(config_path=config_path)
    return TestClient(app)


def test_health(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_and_put_config(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        initial = client.get("/api/config")
        assert initial.status_code == 200

        payload = {
            "version": 1,
            "updated_at": "2026-02-22T00:00:00Z",
            "services": {
                "jarvis-core": {
                    "enabled": True,
                    "owner": "core-team",
                    "models": {
                        "planner": {
                            "provider": "openai",
                            "model": "gpt-4.1",
                            "temperature": 0.2,
                            "max_tokens": 1200,
                        }
                    },
                    "prompts": {"system": "You are Jarvis Core."},
                }
            },
        }
        saved = client.put("/api/config", json=payload)
        assert saved.status_code == 200

        fetched = client.get("/api/config")
        assert fetched.status_code == 200
        cfg = fetched.json()
        assert "jarvis-core" in cfg["services"]
        assert cfg["services"]["jarvis-core"]["models"]["planner"]["model"] == "gpt-4.1"


def test_put_config_requires_services(tmp_path: Path) -> None:
    with make_client(tmp_path) as client:
        payload = {
            "version": 1,
            "updated_at": "2026-02-22T00:00:00Z",
            "services": {},
        }
        response = client.put("/api/config", json=payload)

    assert response.status_code == 400


def test_prompt_store_merges_action_intent_gate_default(tmp_path: Path) -> None:
    prompts_path = tmp_path / "prompts.yaml"
    prompts_path.write_text(
        """
version: 1
prompts:
  base_system:
    name: Base
    description: test
    content: base prompt
""",
        encoding="utf-8",
    )

    data = PromptStore(prompts_path).load()

    assert "action_intent_gate" in data["prompts"]
    assert "Action Intent Gate" in data["prompts"]["action_intent_gate"]["name"]
    assert "한식 레츠고" in data["prompts"]["action_intent_gate"]["content"]


def test_prompt_store_uses_service_py_fallbacks_for_defaults(tmp_path: Path) -> None:
    data = PromptStore(tmp_path / "missing-prompts.yaml").load()
    prompts = data["prompts"]

    assert "## Core rules" in prompts["base_system"]["content"]
    assert "produce a structured execution plan as JSON" in prompts["deepthink_planning"]["content"]
    assert "Include actions in a JSON array fenced" in prompts["deepthink_execution"]["content"]
    assert "Do NOT include action blocks" in prompts["deepthink_summarize"]["content"]
