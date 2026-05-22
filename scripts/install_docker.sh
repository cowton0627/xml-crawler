#!/usr/bin/env bash
# 從中斷處繼續安裝 Docker Engine。需 sudo 執行: sudo bash install_docker.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "請用 sudo 執行: sudo bash $0" >&2
  exit 1
fi

# 真正的使用者 (sudo 下 $USER 會是 root,要從 SUDO_USER 拿)
TARGET_USER="${SUDO_USER:-$USER}"

echo "==> [1/5] 確認 GPG key 已就位"
if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi

echo "==> [2/5] 寫入 apt 倉庫"
ARCH="$(dpkg --print-architecture)"
CODENAME="$(. /etc/os-release && echo "$VERSION_CODENAME")"
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
cat /etc/apt/sources.list.d/docker.list

echo "==> [3/5] apt update"
apt-get update

echo "==> [4/5] 安裝 docker-ce 套件組"
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> [5/5] 啟用 service + 加入 docker group (user: ${TARGET_USER})"
systemctl enable --now docker
usermod -aG docker "${TARGET_USER}"

echo
echo "完成。請重開 shell 後執行:"
echo "  docker version && docker compose version && docker run --rm hello-world"
