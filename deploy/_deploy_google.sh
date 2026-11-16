#!/bin/sh
set -e
TS=20261116-1343
SITE=/var/www/sites/rex.moscow
NEW=/var/www/sites/.rex-new-$TS
TAR=/tmp/rex-$TS.tar.gz

test -f "$TAR" || { echo "нет архива $TAR"; exit 1; }
rm -rf "$NEW"; mkdir -p "$NEW"
tar -xzf "$TAR" -C "$NEW"
echo "распаковано: $(find "$NEW" -type f | wc -l) файлов"
chown -R www-data:www-data "$NEW"
chmod -R u+rwX,go+rX,go-w "$NEW"
if [ -d "$SITE" ]; then mv "$SITE" "$SITE.old-$TS"; echo "старый каталог -> $SITE.old-$TS"; fi
mv "$NEW" "$SITE"
echo "новый каталог на месте"
nginx -t 2>&1 | tail -2
systemctl reload nginx
echo "nginx reloaded"
sleep 1

echo "--- файл подтверждения Google ---"
curl -sk --resolve rex.moscow:443:127.0.0.1 https://rex.moscow/google20d7eb421f9e86fc.html \
  -w '\nhttp_code=%{http_code} size=%{size_download}\n'
echo "--- мета подтверждения ---"
curl -sk --resolve rex.moscow:443:127.0.0.1 https://rex.moscow/ \
  | grep -o 'yandex-verification" content="[a-f0-9]*"\|google-site-verification" content="[^"]*"\|ym(90016027' | head -5

cd /var/www/sites
last=$(ls -d rex.moscow.old-* | sort | tail -1)
for d in rex.moscow.old-*; do [ "$d" = "$last" ] && continue; rm -rf "$d"; echo "удалён резерв: $d"; done
rm -f /tmp/rex-*.tar.gz /tmp/rex-deploy.sh
df -h /var | tail -1
