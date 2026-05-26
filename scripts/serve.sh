#!/usr/bin/env bash
# 啟動 Web UI (FastAPI + uvicorn)。綁 127.0.0.1 - 只給本機用,不對外。
# 用法: ./scripts/serve.sh [port]   (預設 8000)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

PORT="${1:-8000}"

# 確保 RSSHub 在跑 (web UI 加新訂閱要靠它)
docker compose up -d --quiet-pull >/dev/null 2>&1 || true

exec ./.venv/bin/uvicorn app:app --host 127.0.0.1 --port "$PORT"
