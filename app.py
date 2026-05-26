"""xml-crawler Web UI - 自用版本,綁 127.0.0.1。

啟動: ./scripts/serve.sh
"""
from __future__ import annotations

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from crawler import (
    PLATFORMS,
    ROOT,
    RSSHUB_BASE,
    TIMEOUT_SECONDS,
    add_feed_entry,
    build_subscription,
    feed_public_url,
    fetch_one,
    git_push_changes,
    is_name_taken,
    load_feeds,
)

app = FastAPI(title="xml-crawler")


class AddRequest(BaseModel):
    platform: str
    handle: str


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/platforms")
def list_platforms():
    return {"platforms": list(PLATFORMS)}


@app.get("/api/feeds")
def list_subscriptions():
    items = []
    for entry in load_feeds():
        name = entry.get("name")
        if not name:
            continue
        items.append(
            {
                "name": name,
                "route": entry.get("route"),
                "url": entry.get("url"),
                "public_url": feed_public_url(name),
            }
        )
    return {"feeds": items}


@app.post("/api/add")
def add_subscription(req: AddRequest):
    # 1. 解析 platform + handle → (name, route)
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            name, route = build_subscription(req.platform, req.handle, client)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))

    if is_name_taken(name):
        raise HTTPException(409, f"已訂閱: {name}")

    # 2. 寫進 config.yaml
    add_feed_entry(name, route=route)

    # 3. 立刻抓一次 — 確認 RSSHub 路由 work、把 feeds/<name>.xml 生出來
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        success, msg = fetch_one(client, name, f"{RSSHUB_BASE}{route}")
    if not success:
        raise HTTPException(502, f"RSSHub 抓不到: {msg}")

    # 4. git commit + push (push 到當前 branch,merge 到 main 才會觸發 Pages 部署)
    try:
        git_push_changes(
            f"feeds: add {name}",
            ["config.yaml", f"feeds/{name}.xml"],
        )
    except Exception as e:
        raise HTTPException(500, f"git push 失敗: {e}")

    return {"name": name, "public_url": feed_public_url(name)}
