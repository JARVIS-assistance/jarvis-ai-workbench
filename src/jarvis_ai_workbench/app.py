from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .config_store import ConfigStore
from .schemas import ConfigEnvelope


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


def create_app(config_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="jarvis-ai-workbench", version="0.1.0")
    store = ConfigStore(config_path or _workspace_root() / "jarvis-ai-workbench" / "config" / "jarvis-ai.yaml")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "jarvis-ai-workbench"}

    @app.get("/api/config", response_model=ConfigEnvelope)
    def get_config() -> dict[str, Any]:
        return store.load()

    @app.put("/api/config", response_model=ConfigEnvelope)
    def put_config(payload: ConfigEnvelope) -> dict[str, Any]:
        if not payload.services:
            raise HTTPException(status_code=400, detail="services must not be empty")
        return store.save(payload.model_dump())

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _render_html()

    return app


def _render_html() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Jarvis AI Workbench</title>
  <style>
    :root {
      --bg: #f7f8f5;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #6b7280;
      --accent: #0f766e;
      --warn: #b45309;
      --border: #e5e7eb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Noto Sans KR", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 10% 10%, #d1fae5, transparent 35%),
                  radial-gradient(circle at 95% 0%, #fef3c7, transparent 25%),
                  var(--bg);
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 24px; }
    .top {
      display: flex; justify-content: space-between; align-items: center; gap: 12px;
      margin-bottom: 18px;
    }
    h1 { margin: 0; font-size: 28px; letter-spacing: 0.3px; }
    .sub { color: var(--muted); margin-top: 6px; }
    .toolbar { display: flex; gap: 8px; }
    button {
      border: 1px solid var(--border);
      padding: 10px 14px;
      border-radius: 10px;
      background: white;
      cursor: pointer;
      font-weight: 600;
    }
    button.primary { background: var(--accent); color: white; border-color: var(--accent); }
    .meta {
      padding: 10px 12px;
      background: #ecfeff;
      border: 1px solid #a5f3fc;
      border-radius: 12px;
      margin-bottom: 16px;
      font-size: 14px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 14px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      box-shadow: 0 3px 8px rgba(0,0,0,0.03);
    }
    .card h3 { margin: 0 0 8px 0; }
    .kv { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
    textarea {
      width: 100%;
      min-height: 220px;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      line-height: 1.45;
      resize: vertical;
      background: #fcfcfc;
    }
    .status { margin-top: 12px; font-size: 13px; }
    .ok { color: var(--accent); }
    .err { color: var(--warn); }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"top\">
      <div>
        <h1>Jarvis AI Workbench</h1>
        <div class=\"sub\">Prompt Engineering + Model Settings Dashboard</div>
      </div>
      <div class=\"toolbar\">
        <button id=\"refresh\">Refresh</button>
        <button class=\"primary\" id=\"save\">Save All</button>
      </div>
    </div>

    <div id=\"meta\" class=\"meta\">Loading config...</div>
    <div id=\"cards\" class=\"grid\"></div>
    <div id=\"status\" class=\"status\"></div>
  </div>

<script>
let current = null;

function esc(s) {
  return s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

function render(cfg) {
  current = cfg;
  document.getElementById('meta').textContent = `version=${cfg.version} | updated_at=${cfg.updated_at}`;
  const cards = document.getElementById('cards');
  cards.innerHTML = '';

  for (const [name, item] of Object.entries(cfg.services)) {
    const div = document.createElement('div');
    div.className = 'card';
    const content = JSON.stringify(item, null, 2);
    div.innerHTML = `
      <h3>${esc(name)}</h3>
      <div class=\"kv\">enabled=${item.enabled} | owner=${item.owner || '-'}</div>
      <textarea id=\"ta-${name}\">${esc(content)}</textarea>
    `;
    cards.appendChild(div);
  }
}

async function loadConfig() {
  const res = await fetch('/api/config');
  if (!res.ok) {
    throw new Error('failed to load config');
  }
  const cfg = await res.json();
  render(cfg);
}

async function saveConfig() {
  if (!current) return;
  const next = {
    version: current.version || 1,
    updated_at: current.updated_at || new Date().toISOString(),
    services: {},
  };

  for (const name of Object.keys(current.services)) {
    const ta = document.getElementById(`ta-${name}`);
    try {
      next.services[name] = JSON.parse(ta.value);
    } catch (e) {
      setStatus(`Invalid JSON in ${name}: ${e.message}`, true);
      return;
    }
  }

  const res = await fetch('/api/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(next),
  });

  if (!res.ok) {
    const text = await res.text();
    setStatus(`Save failed: ${text}`, true);
    return;
  }
  const updated = await res.json();
  render(updated);
  setStatus('Saved successfully.', false);
}

function setStatus(msg, isErr) {
  const el = document.getElementById('status');
  el.textContent = msg;
  el.className = 'status ' + (isErr ? 'err' : 'ok');
}

document.getElementById('refresh').addEventListener('click', async () => {
  try { await loadConfig(); setStatus('Refreshed.', false); }
  catch (e) { setStatus(e.message, true); }
});

document.getElementById('save').addEventListener('click', async () => {
  try { await saveConfig(); }
  catch (e) { setStatus(e.message, true); }
});

loadConfig().catch(e => setStatus(e.message, true));
</script>
</body>
</html>"""


app = create_app()
