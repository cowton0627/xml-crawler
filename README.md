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

```bash
crontab -e
# 加一行 (每 30 分):
# */30 * * * * cd /home/cowton/projects/xml-crawler && .venv/bin/python fetch_feeds.py >> fetch.log 2>&1
```

---

## 加新訂閱

1. 編輯 `config.yaml`,加一個 `feeds:` 項目
2. `python fetch_feeds.py` 跑一次看是否產生對應 `feeds/<name>.xml`
3. `git add feeds/ config.yaml && git commit && git push`
4. 在 RSS reader 訂閱 `https://<你的帳號>.github.io/xml-crawler/feeds/<name>.xml`

如何找各平台的路由參數,見 [RSSHub Routes](https://docs.rsshub.app/routes/)。

---

## 已知限制

- IG 需要登入 cookie,**請用分身帳號**,本帳可能被限速
- FB 只能抓 Public Page,個人塗鴉牆/私人社團抓不到
- RSSHub 路由偶爾隨平台改版失效,需要 `docker compose pull && up -d` 更新 image
- cron 間隔別低於 30 分,避免被反爬偵測
