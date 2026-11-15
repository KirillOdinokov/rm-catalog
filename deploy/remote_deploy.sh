#!/bin/sh
# Деплой обновлённого dist rex.moscow (атомарная подмена каталога).
set -e
TS=20261114-2350
SITE=/var/www/sites/rex.moscow
NEW=/var/www/sites/.rex-new-$TS
TAR=/tmp/rex-$TS.tar.gz

test -f "$TAR" || { echo "нет архива $TAR"; exit 1; }
rm -rf "$NEW"
mkdir -p "$NEW"
tar -xzf "$TAR" -C "$NEW"
echo "распаковано: $(find "$NEW" -type f | wc -l) файлов"

chown -R www-data:www-data "$NEW"
chmod -R u+rwX,go+rX,go-w "$NEW"

if [ -d "$SITE" ]; then
  mv "$SITE" "$SITE.old-$TS"
  echo "старый каталог -> $SITE.old-$TS"
fi
mv "$NEW" "$SITE"
echo "новый каталог на месте"

nginx -t 2>&1 | tail -2
systemctl reload nginx
echo "nginx reloaded"
sleep 1

echo "--- проверки ---"
for u in / /shop /reks-elast-100 /reks-gidrolenta /dostavka; do
  code=$(curl -sk -o /dev/null -w '%{http_code}' --resolve rex.moscow:443:127.0.0.1 "https://rex.moscow$u")
  echo "$u -> $code"
done
echo "--- цена эласт 100 ---"
curl -sk --resolve rex.moscow:443:127.0.0.1 https://rex.moscow/reks-elast-100 | grep -o 'prod__price">[^<]*' | head -1 || true
echo "--- css version ---"
curl -sk --resolve rex.moscow:443:127.0.0.1 https://rex.moscow/ | grep -o 'site.css?v=[0-9]*' | head -1 || true
