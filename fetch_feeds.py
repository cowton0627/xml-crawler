#!/usr/bin/env python3
"""CLI 入口:讀 config.yaml,從本機 RSSHub 拉每個訂閱的 XML,寫進 feeds/。

執行: python fetch_feeds.py
"""
from __future__ import annotations

import sys

import httpx

from crawler import (
    FEEDS_DIR,
    TIMEOUT_SECONDS,
    fetch_one,
    load_feeds,
    resolve_url,
)


def main() -> int:
    FEEDS_DIR.mkdir(exist_ok=True)
    feeds = load_feeds()
    if not feeds:
        sys.exit("config.yaml 沒有任何 feeds 項目")

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
