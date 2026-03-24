# jarvis-ai-workbench

Jarvis 전반의 AI 구성(프롬프트 엔지니어링 + 모델 설정)을 UI로 조회/수정하는 개발 도구입니다.

## Features

- 서비스별 AI 설정 조회 (`jarvis-core`, `jarvis-controller`, `jarvis-gateway`, `jarvis-contracts`)
- 프롬프트/모델 파라미터 편집
- YAML 파일 저장 (`config/jarvis-ai.yaml`)

## Install

```bash
python3.12 -m pip install -r requirements-dev.txt
```

## Run

```bash
python3.12 -m uvicorn jarvis_ai_workbench.app:app --reload --port 8010
```

or

```bash
./start.sh
```

## Test

```bash
python3.12 -m pytest
```

## Lint

```bash
ruff check .
```
