#!/bin/bash
# Разворачивание rex.moscow на 109.95.77.86 (webnara).
# Запуск: sudo bash ~/deploy_rex.sh
set -e

DOMAIN=rex.moscow
ROOT=/var/www/$DOMAIN/public
SRC=/home/kirill/rex-dist.tar.gz
CONF=/home/kirill/rex.moscow.conf
CERTDIR=/etc/letsencrypt/live/$DOMAIN

echo "== 1. каталог сайта =="
mkdir -p "$ROOT"
tar xzf "$SRC" -C "$ROOT"
chown -R www-data:www-data /var/www/$DOMAIN
find "$ROOT" -type d -exec chmod 755 {} \;
find "$ROOT" -type f -exec chmod 644 {} \;
echo "файлов: $(find "$ROOT" -type f | wc -l)"

echo "== 2. сертификат =="
mkdir -p "$CERTDIR"
cp /home/kirill/certs/fullchain.pem "$CERTDIR/fullchain.pem"
cp /home/kirill/certs/privkey.pem "$CERTDIR/privkey.pem"
chmod 600 "$CERTDIR"/*.pem
chown root:root "$CERTDIR"/*.pem

echo "== 3. vhost =="
cp "$CONF" /etc/nginx/sites-available/$DOMAIN.conf
ln -sf /etc/nginx/sites-available/$DOMAIN.conf /etc/nginx/sites-enabled/$DOMAIN.conf
nginx -t
systemctl reload nginx

echo "== 4. проверка =="
for u in / /shop /reks-elast-100 /sitemap.xml /assets/site.css /no-such-page; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $DOMAIN" "http://127.0.0.1$u")
  echo "$code $u"
done
for u in / /reks-elast-100; do
  code=$(curl -sk -o /dev/null -w '%{http_code}' --resolve "$DOMAIN:443:127.0.0.1" "https://$DOMAIN$u")
  echo "$code https://$u"
done
echo "готово"
