#!/usr/bin/env python3
"""讀 config.yaml,從本機 RSSHub 拉每個訂閱的 XML,寫進 feeds/。

執行: python fetch_feeds.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
FEEDS_DIR = ROOT / "feeds"
RSSHUB_BASE = "http://localhost:1200"
TIMEOUT_SECONDS = 60


def load_config() -> list[dict]:
    with CONFIG_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    feeds = data.get("feeds") or []
    if not feeds:
        sys.exit("config.yaml 沒有任何 feeds 項目")
    return feeds


def resolve_url(entry: dict) -> str | None:
    """支援兩種寫法: url (直接抓) 或 route (拼 RSSHub base)."""
    if entry.get("url"):
        return entry["url"]
    if entry.get("route"):
        return f"{RSSHUB_BASE}{entry['route']}"
    return None


def fetch_one(client: httpx.Client, name: str, url: str) -> tuple[bool, str]:
    try:
        resp = client.get(url, follow_redirects=True)
    except httpx.HTTPError as e:
        return False, f"連線失敗: {e}"

    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

    body = resp.text
    if "<rss" not in body and "<feed" not in body:
        return False, f"回應不是 RSS/Atom (前 200 字: {body[:200]})"

    target = FEEDS_DIR / f"{name}.xml"
    target.write_text(body, encoding="utf-8")
    return True, f"{len(body)} bytes → {target.relative_to(ROOT)}"


def main() -> int:
    FEEDS_DIR.mkdir(exist_ok=True)
    feeds = load_config()

    ok_count = 0
    fail_count = 0
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        for entry in feeds:
            name = entry.get("name")
            url = resolve_url(entry)
            if not name or not url:
                print(f"[SKIP] 缺 name 或 url/route: {entry}")
                continue

            print(f"[FETCH] {name}  ←  {url}")
            success, msg = fetch_one(client, name, url)
            print(f"  {'OK' if success else 'FAIL'}: {msg}")
            if success:
                ok_count += 1
            else:
                fail_count += 1

    print(f"\n總計: {ok_count} 成功, {fail_count} 失敗")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
