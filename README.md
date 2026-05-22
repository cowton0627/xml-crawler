# xml-crawler

抓 YouTube / Threads / Instagram / Facebook 公開內容,產生 RSS XML,推上 GitHub Pages 給雲端 RSS reader 訂閱。

底層用 [RSSHub](https://github.com/DIYgod/RSSHub) (Docker) 跑路由,Python 腳本定時拉 XML、寫進 `feeds/`、git push。

---

## 架構

```
RSSHub (Docker, localhost:1200) ──curl──▶ fetch_feeds.py ──▶ feeds/*.xml ──git push──▶ GitHub Pages ──▶ Feedly/Inoreader
```

詳細決策見 [DECISIONS.md](./DECISIONS.md)。

---

## 一次性設定

### 1. 裝 Docker (WSL2)

```bash
# Docker Engine
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 重開 shell 讓 group 生效
docker run hello-world  # 驗證
```

### 2. 拷貝環境變數

```bash
cp .env.example .env
# 編輯 .env 填 IG/Threads/FB 帳密 (要用到才填)
```

### 3. 起 RSSHub

```bash
docker compose up -d
curl http://localhost:1200/youtube/user/LinusTechTips  # 驗證
```

### 4. Python 環境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. 設 cron

`scripts/run.sh` 是 cron 入口,做了「確保容器活著 → 抓 feed → 若有變更 commit & push」三件事。

```bash
sudo systemctl enable --now cron
(crontab -l 2>/dev/null | grep -v xml-crawler; \
 echo "*/30 * * * * /home/cowton/projects/xml-crawler/scripts/run.sh >> /home/cowton/projects/xml-crawler/run.log 2>&1") | crontab -
```

驗證: `crontab -l` 應該看到那行。log 看 `tail -f run.log`。

---

## 加新訂閱

1. 編輯 `config.yaml`,加一個 `feeds:` 項目(`url:` 直連或 `route:` 走 RSSHub)
2. 手動跑一次驗證: `./scripts/run.sh` (會抓 + commit + push)
3. 在 RSS reader 訂閱 `https://<你的帳號>.github.io/xml-crawler/feeds/<name>.xml`

### 找 YouTube channel 的 uploads playlist ID

```bash
# 把 @handle 換成你要訂的頻道
curl -sSL -A "Mozilla/5.0" "https://www.youtube.com/@<handle>" \
  | grep -oE '"externalId":"UC[A-Za-z0-9_-]{22}"'
```

拿到 `UCxxxxx...`,把開頭 `UC` 改成 `UU`(就是該頻道的「上傳影片」播放清單 ID),路由用 `/youtube/playlist/UUxxxxx...`。

其他平台路由參考 [RSSHub Routes](https://docs.rsshub.app/)。

---

## 已知限制

- IG 需要登入 cookie,**請用分身帳號**,本帳可能被限速
- FB 只能抓 Public Page,個人塗鴉牆/私人社團抓不到
- RSSHub 路由偶爾隨平台改版失效,需要 `docker compose pull && up -d` 更新 image
- cron 間隔別低於 30 分,避免被反爬偵測
