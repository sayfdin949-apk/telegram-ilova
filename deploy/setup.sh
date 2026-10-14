#!/bin/bash
# Noon Telegram ilova — Ubuntu 24.04 VPS ni sozlash (root sifatida). Qayta ishga tushirsa bo'ladi.
#   bash setup.sh DOMEN /root/noon.tar.gz            -> to'liq sozlash (birinchi marta)
#   bash setup.sh DOMEN /root/noon.tar.gz --faqat-kod -> faqat kod/kontentni yangilash va qayta ishga tushirish
# data/ (baza, secret.key), server/.env, log/ va backup/ ga hech qachon tegilmaydi.
set -euo pipefail
DOMEN="${1:?domen kerak}"
PAKET="${2:?paket kerak}"
REJIM="${3:-}"
APP=/opt/noon
export DEBIAN_FRONTEND=noninteractive

if [ "$REJIM" != "--faqat-kod" ]; then
  echo "== paketlar"
  apt-get update -y -q
  apt-get install -y -q python3 python3-venv sqlite3 ufw curl gpg
  if ! command -v caddy >/dev/null 2>&1; then
    apt-get install -y -q caddy || {
      # Ubuntu omborida bo'lmasa — Caddy ning rasmiy ombori
      curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
      curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > /etc/apt/sources.list.d/caddy-stable.list
      apt-get update -y -q && apt-get install -y -q caddy
    }
  fi
  timedatectl set-timezone Asia/Tashkent || true
  id -u noon >/dev/null 2>&1 || useradd --system --home-dir "$APP" --shell /usr/sbin/nologin noon
  echo "== xavfsizlik devori (faqat SSH, 80, 443)"
  ufw allow OpenSSH >/dev/null
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
  ufw --force enable >/dev/null
fi

echo "== kod va kontent"
mkdir -p "$APP" "$APP/data" "$APP/log" "$APP/backup"
NEW="$APP/.yangi"
rm -rf "$NEW"; mkdir -p "$NEW"
tar -xzf "$PAKET" -C "$NEW"
for d in server web video deploy; do
  [ -d "$NEW/$d" ] || continue
  if [ "$d" = server ] && [ -f "$APP/server/.env" ]; then cp -p "$APP/server/.env" "$NEW/server/.env"; fi
  rm -rf "$APP/$d.eski"; [ -d "$APP/$d" ] && mv "$APP/$d" "$APP/$d.eski"
  mv "$NEW/$d" "$APP/$d"
done
rm -rf "$NEW" "$APP"/*.eski
chown -R noon:noon "$APP"
chmod 600 "$APP/server/.env" 2>/dev/null || true

echo "== python muhiti"
[ -x "$APP/venv/bin/python" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q --upgrade pip
"$APP/venv/bin/pip" install -q -r "$APP/deploy/requirements.txt"
chown -R noon:noon "$APP/venv"

echo "== HTTPS (Caddy) va xizmat"
cat > /etc/caddy/Caddyfile <<EOF
$DOMEN {
	encode gzip
	reverse_proxy 127.0.0.1:8790
}
EOF
systemctl reload caddy 2>/dev/null || systemctl restart caddy
install -m 644 "$APP/deploy/noon.service" /etc/systemd/system/noon.service
install -m 755 "$APP/deploy/noon-backup" /etc/cron.daily/noon-backup
systemctl daemon-reload
systemctl enable noon >/dev/null 2>&1

if [ -f "$APP/server/.env" ] && grep -q '^TALABA_BOT_TOKEN=' "$APP/server/.env"; then
  systemctl restart noon
  sleep 8
  systemctl is-active --quiet noon && echo "NATIJA: noon ishlayapti" || { echo "NATIJA: noon ishga tushmadi"; journalctl -u noon -n 30 --no-pager; exit 1; }
else
  echo "NATIJA: o'rnatildi; tokenlar hali yo'q (kochir bosqichida yuboriladi)"
fi
