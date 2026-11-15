#!/bin/sh
# Добавляет 301 для дубля товара /hacut-ochistitel-2 и перезагружает nginx.
set -e
CONF=/etc/nginx/sites-available/delivery-rex.moscow-ssl.conf
TS=$(date +%Y%m%d-%H%M%S)
LINE='    rewrite ^/hacut-ochistitel-2/?$ /hacut-ochistitel permanent;'

if grep -q "hacut-ochistitel-2" "$CONF"; then
  echo "правило уже есть"
else
  cp "$CONF" "/root/rex-vhost-$TS.conf"
  echo "бэкап: /root/rex-vhost-$TS.conf"
  sed -i "/# trailing slash on flat pages/i\\$LINE" "$CONF"
fi
grep -n "hacut-ochistitel" "$CONF" || true

if nginx -t >/tmp/rex-nginx-t 2>&1; then
  tail -1 /tmp/rex-nginx-t
  systemctl reload nginx
  echo "nginx reloaded"
else
  echo "ОШИБКА конфигурации, откат"
  tail -3 /tmp/rex-nginx-t
  cp "/root/rex-vhost-$TS.conf" "$CONF"
  nginx -t >/tmp/rex-nginx-t2 2>&1 || true
  tail -1 /tmp/rex-nginx-t2
  exit 1
fi

echo "--- проверки ---"
for u in /hacut-ochistitel-2 /hacut-ochistitel-2/ /hacut-ochistitel; do
  out=$(curl -sk -o /dev/null -w '%{http_code} %{redirect_url}' --resolve rex.moscow:443:127.0.0.1 "https://rex.moscow$u")
  echo "$u -> $out"
done
