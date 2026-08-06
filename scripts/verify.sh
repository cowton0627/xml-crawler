#!/usr/bin/env bash
# 部署後驗證: 在 PVE 容器(hostname xml-crawler)上跑,證明線上正常運作。
# 用法: ssh xml-crawler 'cd ~/projects/xml-crawler && ./scripts/verify.sh'
# 任一項失敗 → 印 FAIL 並以非 0 結束(可接到 CI / 部署腳本後面)。
set -uo pipefail
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

SERVICE="xml-crawler"
WEB="http://127.0.0.1:8000"
fails=0
pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; fails=$((fails + 1)); }

echo "==== verify $(date -Iseconds) ===="

# ① 版本對齊: 本地 HEAD 不應落後 origin/main(落後代表沒 pull 到最新)
echo "① 版本對齊"
git fetch origin main --quiet 2>/dev/null || true
behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
head=$(git rev-parse --short HEAD)
if [ "$behind" = "0" ]; then
  pass "HEAD=$head 與 origin/main 對齊"
else
  fail "HEAD=$head 落後 origin/main $behind 個 commit — 需 git pull --rebase"
fi

# ② systemd 服務
echo "② systemd 服務"
state=$(systemctl is-active "$SERVICE" 2>/dev/null || true)
[ "$state" = "active" ] && pass "$SERVICE=$state" || fail "$SERVICE=$state (非 active)"

# ③ Web API 回應
echo "③ Web API"
n_feeds=$(curl -s --max-time 10 "$WEB/api/feeds" \
  | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('feeds',[])))" 2>/dev/null || echo "")
if [ -n "$n_feeds" ] && [ "$n_feeds" -gt 0 ] 2>/dev/null; then
  pass "$WEB/api/feeds 回 $n_feeds 筆訂閱"
else
  fail "$WEB/api/feeds 無有效回應 (n_feeds='$n_feeds')"
fi

# ④ RSSHub + Redis 容器
echo "④ RSSHub"
running=$(docker compose ps --status running 2>/dev/null || true)
echo "$running" | grep -q "rsshub" && pass "rsshub 容器 running" || fail "rsshub 容器沒在跑"

# ⑤ 過濾程式碼 smoke test(用線上 venv 實跑 apply_filter)
echo "⑤ 過濾 smoke test"
smoke=$(./.venv/bin/python - <<'PY' 2>/dev/null
from crawler import apply_filter
s = ('<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>'
     '<item><title>開箱評測</title><description>a</description><link>http://x/1</link><guid>1</guid></item>'
     '<item><title>日常</title><description>b</description><link>http://x/2</link><guid>2</guid></item>'
     '</channel></rss>')
out, n = apply_filter(s, {"include": ["開箱"]})
ok_inc = (n == 1 and "開箱" in out and "日常" not in out)
out2, n2 = apply_filter(s, None)
ok_none = (n2 == 0 and out2 == s)
print("OK" if (ok_inc and ok_none) else "BAD")
PY
)
[ "$smoke" = "OK" ] && pass "apply_filter include/無filter 行為正確" || fail "apply_filter smoke test 未通過 (got='$smoke')"

echo "===================="
if [ "$fails" -eq 0 ]; then
  echo "全部通過 ✓"
  exit 0
else
  echo "$fails 項失敗 ✗"
  exit 1
fi
