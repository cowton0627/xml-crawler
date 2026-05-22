# 架構決策紀錄

## YouTube 的取得方式幾經調整,最後選 RSSHub playlist 路由

依序排除:

1. **YouTube 官方 `/feeds/videos.xml?channel_id=<id>`** — 2026-05 實測對所有頻道(含 MKBHD 等大頻道)一律 404。Google 這幾年陸續砍/限縮此 endpoint,不能再用
2. **RSSHub `/youtube/channel/<id>`** — 用 `youtubejs` 抓 YT 內部 API,被 YT 結構改版打壞,503 "this route is empty"
3. **RSSHub `/youtube/playlist/<playlist_id>`** ✅ — 改抓「uploads playlist」(每個頻道自動有一個包含所有上傳的播放清單,ID 就是把 channel ID 的 `UC` 改成 `UU`),這條路徑走的是 playlist API 不是 channel API,目前 work
4. 備案:YouTube Data API v3 + 自己生 RSS。免費 quota 10000/day 夠用,但要去 Google Cloud Console 申請 key,複雜度較高,目前不選

`fetch_feeds.py` 仍支援 `url:` 直連寫法,留給未來有官方 feed 的來源用。

## 為什麼用 RSSHub,不自己寫爬蟲

* IG / FB / Threads 反爬機制重,自己寫要處理 Cloudflare、JS 渲染、cookie 過期、A/B 測試版面變化
* RSSHub 是維護中的開源專案,上百個路由,社群已踩過絕大多數雷
* 我們只負責「拉 XML 存檔 + git push」,介面穩定,變動風險低
* 若哪天 RSSHub 某路由失效,可以單獨換掉那個來源,不會整套垮

## 為什麼用 GitHub Pages,不開 Cloudflare Tunnel

| 方案 | 機器需常開 | 即時性 | 複雜度 | 選擇理由 |
|---|---|---|---|---|
| Cloudflare Tunnel | 必須 | 即時 | 中 | 工作站不一定常開,拒絕 |
| GitHub Pages | 否 | 看 cron | 低 | **選此**:本機產完推上去就行 |
| VPS | 否 (VPS 常開) | 即時 | 中 | 不想付月費,拒絕 |

代價:訂閱清單 (config.yaml + feeds/) 是公開的。但訂的內容本來就是公開帳號,可接受。

## 為什麼 IG 用分身帳,不用本帳

* IG 對「異常 API 流量」會限速或暫時鎖帳號
* 本帳被鎖會影響日常使用,分身帳被鎖只要重開一個
* cookie 過期也只是分身帳要重新登入,不影響本帳

## 為什麼用 Python,不用 Node

* 抓取邏輯主要是 HTTP + YAML 解析 + 寫檔,Python 標準庫就夠
* 不需要 Node 的 ecosystem (我們不做 web UI)
* 跟 RSSHub (Node 寫的) 解耦,RSSHub 只透過 HTTP 對接

## 為什麼 cron 間隔 ≥ 30 分

* IG / FB 對短間隔抓取極敏感,容易被當 bot
* RSS reader (Feedly 等) 本身刷新間隔通常也是 30~60 分,更密也沒意義
* git push 太頻繁會讓 repo 歷史膨脹

## 為什麼不直接讓 RSS reader 連 RSSHub

* 雲端 reader 需要公開 URL,等於要把本機 RSSHub 暴露到公網
* 暴露 RSSHub 等於暴露 IG cookie 等敏感資料 (放在 RSSHub 環境變數)
* 中間多一層 fetch + 寫檔,可以加 retry、過濾、合併、改寫,未來彈性大
