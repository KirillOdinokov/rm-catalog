#!/bin/sh
set -e
TS=20261118-1815
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
echo "--- починенные обложки ---"
for s in beton-kontakt-dlya-chego-prednaznachen betonkontakt-instruktsiya-po-primeneniyu importozameshhenie-stroitelnoj-himii; do
  echo "  $s : $(curl -sk $R -o /dev/null -w '%{http_code} %{size_download} байт' https://rex.moscow/assets/img/a/$s.webp)"
done
echo "--- обложек в сборке ---"
ls "$SITE/assets/img/a" | wc -l
echo "--- страницы ---"
for u in / /blog /importozameshhenie-stroitelnoj-himii /beton-kontakt-dlya-chego-prednaznachen; do
  echo "  $u : $(curl -sk $R -o /dev/null -w '%{http_code}' https://rex.moscow$u)"
done

cd /var/www/sites
last=$(ls -d rex.moscow.old-* | sort | tail -1)
for d in rex.moscow.old-*; do [ "$d" = "$last" ] && continue; rm -rf "$d"; echo "удалён резерв: $d"; done
rm -f /tmp/rex-*.tar.gz /tmp/rex-deploy.sh
df -h /var | tail -1
