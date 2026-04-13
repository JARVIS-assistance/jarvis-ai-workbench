from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .config_store import ConfigStore
from .prompt_store import PromptStore
from .schemas import ConfigEnvelope


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[3]


# ── Prompt API 스키마 ──────────────────────────────────────

class PromptUpdateRequest(BaseModel):
    content: str


def create_app(config_path: Path | None = None) -> FastAPI:
    app = FastAPI(title="jarvis-ai-workbench", version="0.2.0")
    root = _workspace_root()
    store = ConfigStore(config_path or root / "config" / "jarvis-ai.yaml")
    prompt_store = PromptStore(root / "config" / "prompts.yaml")

    # ── Health ─────────────────────────────────────────────
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "jarvis-ai-workbench"}

    # ── Config API (기존) ──────────────────────────────────
    @app.get("/api/config", response_model=ConfigEnvelope)
    def get_config() -> dict[str, Any]:
        return store.load()

    @app.put("/api/config", response_model=ConfigEnvelope)
    def put_config(payload: ConfigEnvelope) -> dict[str, Any]:
        if not payload.services:
            raise HTTPException(status_code=400, detail="services must not be empty")
        return store.save(payload.model_dump())

    # ── Prompt API (신규) ──────────────────────────────────
    @app.get("/api/prompts")
    def get_prompts() -> dict[str, Any]:
        return prompt_store.load()

    @app.put("/api/prompts")
    def put_prompts(payload: dict[str, Any]) -> dict[str, Any]:
        if "prompts" not in payload:
            raise HTTPException(status_code=400, detail="prompts field required")
        return prompt_store.save(payload)

    @app.get("/api/prompts/{key}")
    def get_prompt(key: str) -> dict[str, Any]:
        data = prompt_store.load()
        prompt = data.get("prompts", {}).get(key)
        if prompt is None:
            raise HTTPException(status_code=404, detail=f"prompt '{key}' not found")
        return {"key": key, **prompt}

    @app.put("/api/prompts/{key}")
    def put_prompt(key: str, body: PromptUpdateRequest) -> dict[str, Any]:
        prompt_store.update_prompt(key, body.content)
        return {"key": key, "content": body.content, "status": "saved"}

    # ── UI ─────────────────────────────────────────────────
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _render_html()

    return app


def _render_html() -> str:
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Jarvis AI Workbench</title>
  <style>
    :root {
      --bg: #f7f8f5;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #6b7280;
      --accent: #0f766e;
      --accent-light: #d1fae5;
      --warn: #b45309;
      --border: #e5e7eb;
      --radius: 12px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: "IBM Plex Sans", "Noto Sans KR", -apple-system, sans-serif;
      color: var(--ink);
      background: var(--bg);
      min-height: 100vh;
    }

    /* ── Layout ── */
    .header {
      background: white;
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .header h1 { font-size: 22px; font-weight: 700; }
    .header .sub { color: var(--muted); font-size: 13px; margin-top: 2px; }

    /* ── Tabs ── */
    .tab-bar {
      display: flex;
      gap: 0;
      background: white;
      border-bottom: 1px solid var(--border);
      padding: 0 24px;
    }
    .tab-btn {
      padding: 12px 20px;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      color: var(--muted);
      border-bottom: 2px solid transparent;
      transition: all 0.15s;
    }
    .tab-btn:hover { color: var(--ink); }
    .tab-btn.active {
      color: var(--accent);
      border-bottom-color: var(--accent);
    }

    .content { max-width: 1200px; margin: 0 auto; padding: 24px; }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }

    /* ── Prompt Cards ── */
    .prompt-card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      margin-bottom: 16px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .prompt-card-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }
    .prompt-card h3 {
      font-size: 16px;
      font-weight: 600;
    }
    .prompt-card .desc {
      font-size: 13px;
      color: var(--muted);
      margin-top: 2px;
    }
    .prompt-card .key-badge {
      font-size: 11px;
      background: var(--accent-light);
      color: var(--accent);
      padding: 3px 8px;
      border-radius: 6px;
      font-weight: 600;
      white-space: nowrap;
    }

    textarea.prompt-editor {
      width: 100%;
      min-height: 200px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px;
      line-height: 1.55;
      resize: vertical;
      background: #fafbfc;
      transition: border-color 0.15s;
    }
    textarea.prompt-editor:focus {
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
    }
    textarea.prompt-editor.modified {
      border-color: var(--warn);
      background: #fffbeb;
    }

    /* ── Buttons ── */
    .btn-row {
      display: flex;
      gap: 8px;
      margin-top: 10px;
      justify-content: flex-end;
    }
    button.btn {
      border: 1px solid var(--border);
      padding: 8px 16px;
      border-radius: 8px;
      background: white;
      cursor: pointer;
      font-size: 13px;
      font-weight: 600;
      transition: all 0.15s;
    }
    button.btn:hover { background: #f9fafb; }
    button.btn.primary {
      background: var(--accent);
      color: white;
      border-color: var(--accent);
    }
    button.btn.primary:hover { background: #0d9488; }
    button.btn.save-all {
      background: var(--accent);
      color: white;
      border-color: var(--accent);
      padding: 10px 24px;
      font-size: 14px;
    }

    /* ── Status ── */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      padding: 12px 20px;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 500;
      color: white;
      opacity: 0;
      transform: translateY(10px);
      transition: all 0.3s;
      z-index: 999;
    }
    .toast.show { opacity: 1; transform: translateY(0); }
    .toast.ok { background: var(--accent); }
    .toast.err { background: var(--warn); }

    /* ── Config tab (기존) ── */
    .config-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 14px;
    }
    .config-card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .config-card h3 { margin-bottom: 8px; }
    .config-card .kv { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
    textarea.config-editor {
      width: 100%;
      min-height: 200px;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      line-height: 1.45;
      resize: vertical;
      background: #fafbfc;
    }

    .save-bar {
      position: sticky;
      bottom: 0;
      background: white;
      border-top: 1px solid var(--border);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
    }
    .save-bar .info { font-size: 13px; color: var(--muted); }
  </style>
</head>
<body>

  <div class="header">
    <div>
      <h1>Jarvis AI Workbench</h1>
      <div class="sub">Prompt Engineering &amp; System Configuration</div>
    </div>
  </div>

  <div class="tab-bar">
    <button class="tab-btn active" data-tab="prompts">System Prompts</button>
    <button class="tab-btn" data-tab="config">Service Config</button>
  </div>

  <div class="content">
    <!-- ═══ Prompts Tab ═══ -->
    <div id="tab-prompts" class="tab-panel active">
      <div id="prompt-cards"></div>
      <div class="save-bar">
        <div class="info" id="prompt-info">Loading...</div>
        <div style="display:flex; gap:8px;">
          <button class="btn" id="prompt-refresh">Refresh</button>
          <button class="btn save-all" id="prompt-save-all">Save All</button>
        </div>
      </div>
    </div>

    <!-- ═══ Config Tab ═══ -->
    <div id="tab-config" class="tab-panel">
      <div id="config-meta" style="padding:10px 12px; background:#ecfeff; border:1px solid #a5f3fc; border-radius:12px; margin-bottom:16px; font-size:14px;">
        Loading...
      </div>
      <div id="config-cards" class="config-grid"></div>
      <div class="save-bar">
        <div class="info">Service-level JSON configuration</div>
        <div style="display:flex; gap:8px;">
          <button class="btn" id="config-refresh">Refresh</button>
          <button class="btn save-all" id="config-save">Save All</button>
        </div>
      </div>
    </div>
  </div>

  <div id="toast" class="toast"></div>

<script>
// ── Tab 전환 ──────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
  });
});

// ── Toast ─────────────────────────────────────────────────
function toast(msg, ok = true) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show ' + (ok ? 'ok' : 'err');
  setTimeout(() => el.classList.remove('show'), 3000);
}

function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ═══════════════════════════════════════════════════════════
// Prompts Tab
// ═══════════════════════════════════════════════════════════
let promptData = null;
let originalContents = {};

const PROMPT_ORDER = ['base_system', 'deepthink_planning', 'deepthink_execution', 'deepthink_summarize'];
const PROMPT_HEIGHTS = {
  base_system: '250px',
  deepthink_planning: '350px',
  deepthink_execution: '450px',
  deepthink_summarize: '150px',
};

function renderPrompts(data) {
  promptData = data;
  originalContents = {};
  const container = document.getElementById('prompt-cards');
  container.innerHTML = '';
  const prompts = data.prompts || {};

  const keys = [...PROMPT_ORDER.filter(k => k in prompts), ...Object.keys(prompts).filter(k => !PROMPT_ORDER.includes(k))];

  for (const key of keys) {
    const p = prompts[key];
    originalContents[key] = p.content || '';

    const card = document.createElement('div');
    card.className = 'prompt-card';
    card.innerHTML = `
      <div class="prompt-card-header">
        <div>
          <h3>${esc(p.name || key)}</h3>
          <div class="desc">${esc(p.description || '')}</div>
        </div>
        <span class="key-badge">${esc(key)}</span>
      </div>
      <textarea
        class="prompt-editor"
        id="pe-${key}"
        style="min-height:${PROMPT_HEIGHTS[key] || '200px'}"
      >${esc(p.content || '')}</textarea>
      <div class="btn-row">
        <button class="btn" onclick="resetPrompt('${key}')">Reset</button>
        <button class="btn primary" onclick="saveOnePrompt('${key}')">Save</button>
      </div>
    `;
    container.appendChild(card);

    // 변경 감지
    document.getElementById('pe-' + key).addEventListener('input', function() {
      this.classList.toggle('modified', this.value !== originalContents[key]);
      updatePromptInfo();
    });
  }

  document.getElementById('prompt-info').textContent =
    `version ${data.version || 1} | updated ${data.updated_at || '-'} | ${keys.length} prompts`;
}

function updatePromptInfo() {
  const modified = Object.keys(originalContents).filter(k => {
    const ta = document.getElementById('pe-' + k);
    return ta && ta.value !== originalContents[k];
  });
  const info = document.getElementById('prompt-info');
  if (modified.length > 0) {
    info.textContent = `${modified.length} prompt(s) modified — unsaved`;
    info.style.color = '#b45309';
  } else {
    info.textContent = `All prompts saved | updated ${promptData?.updated_at || '-'}`;
    info.style.color = '';
  }
}

function resetPrompt(key) {
  const ta = document.getElementById('pe-' + key);
  if (ta) {
    ta.value = originalContents[key];
    ta.classList.remove('modified');
    updatePromptInfo();
  }
}

async function saveOnePrompt(key) {
  const ta = document.getElementById('pe-' + key);
  if (!ta) return;
  try {
    const res = await fetch('/api/prompts/' + key, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: ta.value }),
    });
    if (!res.ok) throw new Error(await res.text());
    originalContents[key] = ta.value;
    ta.classList.remove('modified');
    updatePromptInfo();
    toast(`"${key}" saved`);
  } catch (e) { toast(e.message, false); }
}

async function loadPrompts() {
  try {
    const res = await fetch('/api/prompts');
    if (!res.ok) throw new Error('Failed to load prompts');
    renderPrompts(await res.json());
  } catch (e) { toast(e.message, false); }
}

async function saveAllPrompts() {
  if (!promptData) return;
  const next = { ...promptData, prompts: { ...promptData.prompts } };

  for (const key of Object.keys(next.prompts)) {
    const ta = document.getElementById('pe-' + key);
    if (ta) next.prompts[key] = { ...next.prompts[key], content: ta.value };
  }

  try {
    const res = await fetch('/api/prompts', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(next),
    });
    if (!res.ok) throw new Error(await res.text());
    renderPrompts(await res.json());
    toast('All prompts saved');
  } catch (e) { toast(e.message, false); }
}

document.getElementById('prompt-refresh').addEventListener('click', loadPrompts);
document.getElementById('prompt-save-all').addEventListener('click', saveAllPrompts);


// ═══════════════════════════════════════════════════════════
// Config Tab (기존 로직 유지)
// ═══════════════════════════════════════════════════════════
let configData = null;

function renderConfig(cfg) {
  configData = cfg;
  document.getElementById('config-meta').textContent =
    `version=${cfg.version} | updated_at=${cfg.updated_at}`;
  const cards = document.getElementById('config-cards');
  cards.innerHTML = '';
  for (const [name, item] of Object.entries(cfg.services || {})) {
    const div = document.createElement('div');
    div.className = 'config-card';
    div.innerHTML = `
      <h3>${esc(name)}</h3>
      <div class="kv">enabled=${item.enabled} | owner=${item.owner || '-'}</div>
      <textarea class="config-editor" id="ce-${name}">${esc(JSON.stringify(item, null, 2))}</textarea>
    `;
    cards.appendChild(div);
  }
}

async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    if (!res.ok) throw new Error('Failed to load config');
    renderConfig(await res.json());
  } catch (e) { toast(e.message, false); }
}

async function saveConfig() {
  if (!configData) return;
  const next = { version: configData.version || 1, updated_at: configData.updated_at, services: {} };
  for (const name of Object.keys(configData.services || {})) {
    const ta = document.getElementById('ce-' + name);
    try { next.services[name] = JSON.parse(ta.value); }
    catch (e) { toast(`Invalid JSON in ${name}: ${e.message}`, false); return; }
  }
  try {
    const res = await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(next),
    });
    if (!res.ok) throw new Error(await res.text());
    renderConfig(await res.json());
    toast('Config saved');
  } catch (e) { toast(e.message, false); }
}

document.getElementById('config-refresh').addEventListener('click', loadConfig);
document.getElementById('config-save').addEventListener('click', saveConfig);


// ── Init ──────────────────────────────────────────────────
loadPrompts();
loadConfig();
</script>
</body>
</html>"""


app = create_app()
