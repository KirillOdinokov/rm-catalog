#!/bin/sh
set -e
TS=20261118-1740
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
echo "--- обложек в сборке ---"
ls "$SITE/assets/img/a" | wc -l
echo "--- обложка конкретной статьи ---"
curl -sk $R -o /dev/null -w 'cover http=%{http_code} type=%{content_type} bytes=%{size_download}\n' \
  https://rex.moscow/assets/img/a/kak-pravilno-vypolnyat-ankerovku-s-zagibom-kogda-dlina-pryamogo-uchast.webp
curl -sk $R https://rex.moscow/kak-pravilno-vypolnyat-ankerovku-s-zagibom-kogda-dlina-pryamogo-uchast \
  | grep -o 'og:image" content="[^"]*"\|art__cover' | head -3
echo "--- обложек на /blog ---"
curl -sk $R https://rex.moscow/blog | grep -o 'img/a/[a-z0-9-]*\.webp' | wc -l
echo "--- ключевые страницы ---"
for u in / /shop /blog /sitemap_index.xml; do
  echo "  $u : $(curl -sk $R -o /dev/null -w '%{http_code}' https://rex.moscow$u)"
done

cd /var/www/sites
last=$(ls -d rex.moscow.old-* | sort | tail -1)
for d in rex.moscow.old-*; do [ "$d" = "$last" ] && continue; rm -rf "$d"; echo "удалён резерв: $d"; done
rm -f /tmp/rex-*.tar.gz /tmp/rex-deploy.sh
df -h /var | tail -1
