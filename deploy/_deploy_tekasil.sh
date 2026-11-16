#!/bin/sh
set -e
TS=20261116-1615
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

R="--resolve rex.moscow:443:127.0.0.1"
echo "--- TEKASIL: цена по запросу ---"
curl -sk $R https://rex.moscow/tekasil-firestop-silikonovyj-germetik-dlya-protivopozharnyh-shvov \
  | grep -o '<title>[^<]*</title>\|по запросу' | head -3
echo "--- контрольная карточка с ценой ---"
curl -sk $R https://rex.moscow/reks-fiks-epo-t-krasnyj-bystryj-20-min | grep -o '28[ .]733[^<]\{0,12\}' | head -2

cd /var/www/sites
last=$(ls -d rex.moscow.old-* | sort | tail -1)
for d in rex.moscow.old-*; do [ "$d" = "$last" ] && continue; rm -rf "$d"; echo "удалён резерв: $d"; done
rm -f /tmp/rex-*.tar.gz /tmp/rex-deploy.sh
df -h /var | tail -1
