# 架構決策紀錄

## YouTube 的取得方式幾經調整,最後選 RSSHub playlist 路由

依序排除:

1. **YouTube 官方 `/feeds/videos.xml?channel_id=<id>`** — 2026-05 實測對所有頻道(含 MKBHD 等大頻道)一律 404。Google 這幾年陸續砍/限縮此 endpoint,不能再用
2. **RSSHub `/youtube/channel/<id>`** — 用 `youtubejs` 抓 YT 內部 API,被 YT 結構改版打壞,503 "this route is empty"
3. **RSSHub `/youtube/playlist/<playlist_id>`** — 改抓「uploads playlist」(每個頻道自動有一個包含所有上傳的播放清單,ID 就是把 channel ID 的 `UC` 改成 `UU`),這條路徑走的是 playlist API 不是 channel API。**2026-06 已失效**:跟 channel 路由一樣回 503 "this route is empty"(無 API key 的抓取被 YT 打壞)。實測 5/25–5/26 後 feed 就沒再更新,cron 一直 `exit 1`,期間 auto-update 全是 Threads 在動。升級 RSSHub image 到 2026-06-16 build 也沒修好,確認是 YT 端問題不是 image。
4. **YouTube Data API v3 + key** ✅(2026-06-17 啟用)— 無 key 的抓取被 YT 打壞後,改走這條。在 Google Cloud Console(用**個人 gmail**,避開公司 Workspace 的組織政策限制)建專案 → 啟用 YouTube Data API v3 → 建「公開資料」API 金鑰 → API 限制只勾 YouTube Data API v3 → 填進 `.env` 的 `YOUTUBE_KEY`。RSSHub playlist 路由偵測到 key 就改走官方 API,穩定。免費 quota 10000/day 夠用。實測 cowton0517 21 則、taoofhumility 50 則(API 單頁上限)恢復正常。
   - 注意:RSSHub 輸出單行壓縮 XML,驗證 item 數要用 `grep -o '<item>' | wc -l`,別用 `grep -c`(數行數會誤回 1)。

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

## IG 經歷三條死路,最後走鏡像站 picnob

2026-05～06 為了訂 IG 公開帳號,依序撞牆:

1. **`/instagram/2/user/<X>`(web-api,吃 `IG_COOKIE`)** — cookie 本身有效(容器內 `curl` 同 cookie + header 可拿 HTTP 200),但 RSSHub 用的 Node `ofetch`(undici)被 IG 的 TLS/JA3 指紋擋,一律 429。Node 無公開 API 改 TLS 指紋,RSSHub 不會為單一路由引 `curl-impersonate`。**設定問題排除,是架構限制。**
2. **`/instagram/user/<X>`(private-api,吃 `IG_USERNAME`/`IG_PASSWORD`)** — `instagram-private-api` 模擬 App 登入,TLS 指紋不同可繞過第 1 點。但實測即使帳密完全正確(同帳密無痕瀏覽器登入成功、handle 正確、2FA 關閉、住宅 IP 非機房),`/api/v1/accounts/login/` 仍回 `IgLoginBadPasswordError 400 ... we can send you an email`。IG 對「模擬 App API 的自動化登入」偵測精準,軟封鎖。
3. **`/picnob/user/<X>`(第三方鏡像站 picnob.com)** — 2026-06-16 build 起可用,**2026-06-17 起死亡**:picnob.com 升級防護,對非瀏覽器流量一律 403,RSSHub 抓到空頁回「this route is empty」。2026-07-13 升級 RSSHub image 至最新 build 亦無效(是鏡像站端在擋,上游修不了)。
4. **`/picuki/profile/<X>`(鏡像站 picuki.com)** ✅(2026-07-13 起)— 同 build 內的替代鏡像路由,實測 natgeo 35 則、內文正確。已知折衷:**item 無 pubDate**(RSS reader 以首次看到時間排序)、連結指向 picuki.com。

代價/風險:靠第三方鏡像站,會浮動(item 數時多時少)、隨時可能壞;貼文連結指向鏡像站而非 instagram.com。屬「能用就用,壞了再說」——鏡像站是打地鼠,壞了就在 RSSHub 的 `/api/namespace` 清單裡找下一家(picnob → picuki 就是這樣換的)。需登入的官方路線在免費自架前提下實質已死。

## FB 為什麼一直沒做:規劃內、但性價比低而主動略過

2026-08-06 回頭盤點:FB 從專案初期就列在範圍(README 標題、`.env.example` 有 `FB_COOKIE=` 欄位、README「已知限制」寫明「FB 只能抓 Public Page」),**但從未實作**——git log 零 FB commit,`crawler.PLATFORMS` 只有 `youtube/threads/instagram`,`build_subscription` 無 FB 分支。對比 IG 有整段「三條死路」失敗紀錄,FB 一個字都沒有 → 代表**根本沒動手,不是撞牆**。

沒做的理由(排序):
1. **用途太窄**:RSSHub FB route 只能抓公開粉專(Public Page),個人塗鴉牆/私人社團抓不到——想看的個人/朋友貼文本來就拿不到。
2. **又要 cookie/token**:FB route 屬「要登入憑證」那類(`.env.example` 註解:需 Graph API token 或 cookie),跟 IG 同種地雷。IG 已被 cookie 的 TLS 指紋擋、private-api 登入軟封鎖折磨過(見上方 IG 段),FB 可預期一樣痛。
3. **沒有非訂不可的目標**:真正驅動專案的是 YT/Threads/IG,手上沒有一定要訂的 FB 粉專。

2026-08-06 嘗試實作時發現**硬阻塞**:RSSHub 已整個移除 Facebook 支援。實測容器 image(diygod/rsshub:chromium-bundled,3 週前 build)1678 個 namespace 內無 `facebook`,舊路由 `/facebook/page/*` 回 404;upstream master 也無 `lib/routes/facebook`(GitHub API 404、code search 命中 0)。升級 image 救不回來。**結論:走 RSSHub 做 FB 這條路已死。** 唯一剩下的自架路線是 Facebook Graph API,且實務上只有「自己是管理員的粉專」可行(讀任意他人公開粉專需 Page Public Content Access,要 App Review + 商家驗證,個人工具等於做不到)。

**2026-08-06 決議:放棄 FB,收工。** 沒有非訂不可的自有粉專,不值得為 Graph API 的 app/token 維運成本開這個坑;要借 rss.app 那種 SaaS 又破壞純自架前提(它做得到是靠商家驗證 API + 規模化代理/帳號爬取基礎設施,自架複製不了,分析見 knowledgebase-vault `xml-crawler 2026-08-06 FB 訂閱死路與 rss.app 為何做得到`)。專案聚焦 YT / Threads / IG。FB 若哪天真的要,再評估 Graph API。

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

## 線上服務跑在 PVE 容器,開發機只是另一份 clone

`http://xml-crawler:8000/` 的 Web UI 服務跑在 **Proxmox 主機 `pve` 上的 LXC 容器(VMID 200,hostname `xml-crawler`,Tailscale)**,不是開發用的工作站。兩邊都是同一個 repo 的 clone,都 push 回同一個 GitHub origin。

* 部署 = 開發機 `git push` → 容器 `git pull --rebase` →(只在改 Python 時)重啟服務;改 `static/` 因 `app.py` 用 `FileResponse` 即時讀檔,pull 完就生效、免重啟。
* 容器內服務是系統級 systemd unit(`xml-crawler.service`,`User=cowton`、`Restart=on-failure`)。
* 踩過的雷:曾誤把改動只 commit 到開發機那份 clone,線上完全沒吃到——**改線上行為一定要確認自己在對的機器上**。

## 複製按鈕用 execCommand/prompt fallback,不為它上 HTTPS

Web UI 的「複製 feed URL」原本只用 `navigator.clipboard.writeText`,但該 API **只在 secure context(HTTPS 或 localhost)存在**。使用者是用 `http://xml-crawler:8000`(純 HTTP + 非 localhost 主機名)開,`navigator.clipboard` 是 `undefined`,一按就丟錯、什麼都沒複製到。

選擇三層 fallback(secure context 用標準 API → 否則 `document.execCommand('copy')` → 再不行跳 `prompt()` 讓使用者手動 Ctrl+C),而不是為這台內網自用工具去架 HTTPS(反代 + 憑證)。純內網、自用、低頻操作,fallback 的成本/效益遠優於維護 TLS。

## `git_push_changes` push 失敗自動 `pull --rebase` 重試

`/api/add`、`/api/feeds` 退訂、以及 cron 自動更新 feeds 都會 `git push`,而**開發機與 PVE 容器兩份 clone 會各自 push 回同一 origin**,cron 又頻繁自動 push feeds,origin 很容易在某一方 commit 後、push 前就領先 → non-fast-forward 被拒 → 訂閱操作整個失敗報「git push 失敗」。

作法:`git_push_changes` 在 push 被拒時自動 `pull --rebase origin <branch>` 一次再重試。因 feeds/config 各筆改的檔案不重疊,rebase 幾乎不會衝突。已實測驗證:手動製造 origin 領先 1 格後訂閱,reflog 顯示確實走 rebase 把遠端 commit 補回、重放本次 commit 後 push 成功(舊版會回 500)。

## 免密碼重啟:NOPASSWD sudoers 只放行單一指令

容器內服務是系統級 systemd,重啟要 root;但遠端操作(Claude 用 `cowton` ssh 進去)沒有 root 密碼。與其開放整台 sudo,選擇在 `/etc/sudoers.d/xml-crawler` 只放行一條:

```
cowton ALL=(root) NOPASSWD: /usr/bin/systemctl restart xml-crawler
```

權限縮到最小(只能重啟這一個服務),`ssh xml-crawler 'sudo -n systemctl restart xml-crawler'` 即可乾淨重啟。備援:若 sudoers 遺失,可 `kill -9` uvicorn process 靠 `Restart=on-failure` 觸發重生(`kill -9` 屬非乾淨結束才會觸發;SIGTERM 反而被當乾淨、不重啟)。

## 關鍵字過濾放在寫檔前那一層,用 ElementTree 重寫 XML

2026-08-06 加入 `config.yaml` 每個來源可選的 `filter: {include, exclude}`(參考 rss.app 的社群 feed 過濾功能)。實作選擇:

* **位置**:抓回 RSSHub 的 XML 後、寫進 `feeds/` 前套用(`crawler.apply_filter`),過濾後才做 GUID dedup 比對——符合「中間多一層 fetch 可以過濾」(見本檔最末節)。無 `filter` 的來源走原路徑,行為完全不變,零風險。
* **比對範圍只取標題 + 內文**(RSS 的 `title`/`description`/`content:encoded`,Atom 的 `title`/`summary`/`content`),**不碰 `link`/`guid`**——否則像 `ad`、`http` 這種短關鍵字會誤中網址。已寫測試驗證 `exclude:[http]` 不會因 link 含 http 就砍光。
* **語意**:`include` 非空時「只留含任一關鍵字」,`exclude` 命中一律丟(優先於 include),大小寫不敏感、子字串比對(中文可用)。
* **取捨:用 `xml.etree.ElementTree` parse→移除 item→重新序列化**,會把原本 CDATA 包的 `description` 轉成 entity 轉義(`&lt;`),bytes 跟 RSSHub 原輸出不同。語意等價(reader 解 entity 與 CDATA 結果相同),接受此取捨換取不引第三方 XML 套件。為降低影響:**沒有任何 item 被移除時直接回原文、不重新序列化**(大多數抓取不會命中過濾)。用 regex 掃 `xmlns` 宣告 `ET.register_namespace` 回去,保留 `content:`/`atom:` 等 prefix。
* **fail-open**:parse 失敗就原樣寫回,不因過濾把整個 feed 弄壞。
* **範圍**:目前只吃 `config.yaml` 手動設定,Web UI 尚未提供過濾欄位(`add_feed_entry` 不寫 filter)。要 Web 化再說。

## 評估過 crawl4ai,不採用

2026-08-06 評估 [crawl4ai](https://github.com/unclecode/crawl4ai)(開源 LLM-friendly 爬蟲,Playwright + FastAPI,把任意網頁轉 Markdown/JSON 餵 LLM)。**不引入**:

* 目的不同:crawl4ai 服務「LLM 資料流」(產 Markdown/JSON 給 RAG/訓練);本專案服務「人的閱讀流」(產 RSS XML 給 Feedly/Inoreader)。它給你內容,組 RSS 還是得自己寫。
* 太重:每次抓要開一顆完整瀏覽器(Chromium),比走 RSSHub 既有路由重非常多,而我們的來源(YT/Threads/IG/FB)RSSHub 都已覆蓋。
* 唯一可能的交集:某平台 RSSHub 無路由或被擋、需自己爬網頁再組 RSS 時,可當「抓取層」候選。但以目前需求沒必要——與「[為什麼用 RSSHub,不自己寫爬蟲](#為什麼用-rsshub不自己寫爬蟲)」同理。

## 為什麼不直接讓 RSS reader 連 RSSHub

* 雲端 reader 需要公開 URL,等於要把本機 RSSHub 暴露到公網
* 暴露 RSSHub 等於暴露 IG cookie 等敏感資料 (放在 RSSHub 環境變數)
* 中間多一層 fetch + 寫檔,可以加 retry、過濾、合併、改寫,未來彈性大
