#!/usr/bin/env bash
# 啟動 Web UI (FastAPI + uvicorn)。
# 預設綁 0.0.0.0 - WSL2 預設 networking 下,Windows host 跟 SSH tunnel 都靠這個
# 才看得到 WSL2 內的 service。要鎖死本機可手動覆寫 HOST=127.0.0.1。
# 用法: ./scripts/serve.sh [port]   (預設 8000)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

PORT="${1:-8000}"
HOST="${HOST:-0.0.0.0}"

# 確保 RSSHub 在跑 (web UI 加新訂閱要靠它)
docker compose up -d --quiet-pull >/dev/null 2>&1 || true

exec ./.venv/bin/uvicorn app:app --host "$HOST" --port "$PORT"
