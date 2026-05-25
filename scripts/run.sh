#!/usr/bin/env bash
# cron 入口: 確保 RSSHub 在跑、拉所有 feed、若有變更則 commit & push。
# 設計為「部分失敗不中斷」: 個別 feed 失敗不影響其他成功 feed 推上去。
set -uo pipefail

# cron 環境變數極簡,自己補 PATH (要含 docker, git, python)
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

echo "==== $(date -Iseconds) ===="

# 1. 確保 RSSHub + Redis 起來 (已起就 no-op)
docker compose up -d --quiet-pull >/dev/null 2>&1 || true

# 2. 抓所有 feed (用 venv python)
./.venv/bin/python fetch_feeds.py
FETCH_EXIT=$?
echo "fetch_feeds exit: $FETCH_EXIT"

# 3. 沒變更就結束
if git diff --quiet feeds/ && git diff --staged --quiet feeds/; then
  echo "no changes, skip push"
  exit 0
fi

# 4. 有變更: commit + push
git add feeds/
git commit -m "feeds: auto-update $(date -Iseconds)"
git push origin main
echo "pushed"
