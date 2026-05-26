"""xml-crawler 共用核心:讀 config、解析 URL、抓 RSSHub、寫入 feeds/。

CLI 入口在 fetch_feeds.py、Web 入口在 app.py,兩者都 import 這個 module。
"""
from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / "config.yaml"
FEEDS_DIR = ROOT / "feeds"
RSSHUB_BASE = "http://localhost:1200"
TIMEOUT_SECONDS = 60
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def load_feeds() -> list[dict]:
    """讀 config.yaml 拿 feeds list。檔案不存在或空清單都回 []。"""
    if not CONFIG_PATH.exists():
        return []
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("feeds") or []


def resolve_url(entry: dict) -> str | None:
    """支援兩種寫法: url (直接抓) 或 route (拼 RSSHub base)."""
    if entry.get("url"):
        return entry["url"]
    if entry.get("route"):
        return f"{RSSHUB_BASE}{entry['route']}"
    return None


def extract_item_ids(xml_text: str) -> set[str] | None:
    """抓 RSS/Atom 的 item identifier 集合。Parse 失敗或抓不到任何 id 就回 None。

    用 GUID 集合判斷實質變更,避免 <lastBuildDate> 或 CDN URL 浮動 token 造成假變更。
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    ids: set[str] = set()
    for item in root.iter("item"):  # RSS 2.0
        ident = (item.findtext("guid") or item.findtext("link") or "").strip()
        if ident:
            ids.add(ident)
    for entry in root.iter(f"{ATOM_NS}entry"):  # Atom
        ident = (entry.findtext(f"{ATOM_NS}id") or "").strip()
        if ident:
            ids.add(ident)
    return ids or None


def fetch_one(client: httpx.Client, name: str, url: str) -> tuple[bool, str]:
    """抓單一 feed 寫進 feeds/<name>.xml。item 集合未變則保留舊檔。"""
    try:
        resp = client.get(url, follow_redirects=True)
    except httpx.HTTPError as e:
        return False, f"連線失敗: {e}"

    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"

    body = resp.text
    if "<rss" not in body and "<feed" not in body:
        return False, f"回應不是 RSS/Atom (前 200 字: {body[:200]})"

    FEEDS_DIR.mkdir(exist_ok=True)
    target = FEEDS_DIR / f"{name}.xml"
    if target.exists():
        new_ids = extract_item_ids(body)
        old_ids = extract_item_ids(target.read_text(encoding="utf-8"))
        if new_ids is not None and old_ids is not None and new_ids == old_ids:
            return True, f"item 集合未變 ({len(new_ids)} 則),保留舊檔"

    target.write_text(body, encoding="utf-8")
    return True, f"{len(body)} bytes → {target.relative_to(ROOT)}"


def is_name_taken(name: str) -> bool:
    return any(entry.get("name") == name for entry in load_feeds())


def add_feed_entry(
    name: str,
    route: str | None = None,
    url: str | None = None,
    comment: str = "",
) -> None:
    """Append 一筆 entry 到 config.yaml 檔尾,保留現有註解不重寫整個檔。"""
    if not route and not url:
        raise ValueError("route 或 url 至少要有一個")
    if is_name_taken(name):
        raise ValueError(f"name 已存在: {name}")

    block = f"\n  - name: {name}\n"
    if route:
        block += f"    route: {route}\n"
    else:
        block += f"    url: {url}\n"
    if comment:
        block += f"    # {comment}\n"

    with CONFIG_PATH.open("a", encoding="utf-8") as f:
        f.write(block)


def remove_feed_entry(name: str) -> None:
    """從 config.yaml 移除指定 name 的 entry block。

    line-based 操作:找到 `- name: <name>` 那行,刪到下一個 `- name:` 或 EOF。
    這會吃掉 entry 內部的縮排註解 — 接受這個取捨,換取不引入 ruamel.yaml 依賴。
    """
    lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    marker = f"- name: {name}"

    start = None
    for i, line in enumerate(lines):
        if line.strip() == marker:
            start = i
            break
    if start is None:
        raise ValueError(f"找不到 entry: {name}")

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].lstrip().startswith("- name:"):
            end = j
            break

    del lines[start:end]
    CONFIG_PATH.write_text("".join(lines), encoding="utf-8")


# ─── 平台解析 ────────────────────────────────────────────────────────────────

PLATFORMS = ("youtube", "threads", "instagram")
_HANDLE_RE = re.compile(r"[A-Za-z0-9_.-]+")
_AT_HANDLE_RE = re.compile(r"@([A-Za-z0-9_.-]+)")
_YT_CHANNEL_ID_RE = re.compile(r'"externalId":"(UC[A-Za-z0-9_-]{22})"')


def normalize_handle(raw: str) -> str:
    """容錯處理使用者輸入: '@xxx'、'xxx'、整個 URL 都吃。回乾淨的 handle。"""
    raw = raw.strip()
    m = _AT_HANDLE_RE.search(raw)
    if m:
        return m.group(1)
    return raw.lstrip("@").split("/")[0]


def resolve_youtube_playlist_id(handle: str, client: httpx.Client) -> str:
    """從 YouTube @handle 取 uploads playlist ID (UCxxx → UUxxx)。"""
    resp = client.get(
        f"https://www.youtube.com/@{handle}",
        headers={"User-Agent": "Mozilla/5.0"},
        follow_redirects=True,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"YouTube 抓不到 @{handle} (HTTP {resp.status_code})")
    m = _YT_CHANNEL_ID_RE.search(resp.text)
    if not m:
        raise RuntimeError(f"@{handle} 頁面找不到 channel ID")
    return "UU" + m.group(1)[2:]


def build_subscription(
    platform: str, raw_input: str, client: httpx.Client
) -> tuple[str, str]:
    """從 (platform, raw input) 推出 (feed name, RSSHub route)。"""
    if platform not in PLATFORMS:
        raise ValueError(f"不支援的平台: {platform}")

    handle = normalize_handle(raw_input)
    if not handle or not _HANDLE_RE.fullmatch(handle):
        raise ValueError(f"無效的 handle: {raw_input!r}")

    if platform == "youtube":
        playlist_id = resolve_youtube_playlist_id(handle, client)
        return f"youtube-{handle}", f"/youtube/playlist/{playlist_id}"
    if platform == "threads":
        return f"threads-{handle}", f"/threads/{handle}"
    # instagram
    return f"ig-{handle}", f"/instagram/user/{handle}"


# ─── GitHub Pages URL / Git operations ───────────────────────────────────────

_REMOTE_RE = re.compile(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def github_pages_base() -> str:
    """從 git origin URL 推 https://<user>.github.io/<repo>。"""
    url = _git("config", "--get", "remote.origin.url")
    m = _REMOTE_RE.search(url)
    if not m:
        raise RuntimeError(f"無法從 remote URL 推 Pages base: {url}")
    return f"https://{m.group(1)}.github.io/{m.group(2)}"


def feed_public_url(name: str) -> str:
    return f"{github_pages_base()}/feeds/{name}.xml"


def git_push_changes(message: str, paths: list[str]) -> None:
    """加指定路徑、commit、push 當前 branch。沒變更則 skip。"""
    _git("add", *paths)
    status = _git("status", "--porcelain", *paths)
    if not status:
        return
    _git("commit", "-m", message)
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    _git("push", "origin", branch)
