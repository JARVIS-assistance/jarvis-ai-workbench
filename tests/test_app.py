from pathlib import Path

from fastapi.testclient import TestClient

from jarvis_ai_workbench.app import create_app


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
