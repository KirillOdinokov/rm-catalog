#!/bin/sh
set -e
TS=20261116-1415
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
echo "--- sitemap_index.xml ---"
curl -sk $R https://rex.moscow/sitemap_index.xml -o /tmp/sm1.xml -w 'http=%{http_code} type=%{content_type} bytes=%{size_download}\n'
echo "URL в файле: $(grep -c '<loc>' /tmp/sm1.xml)"
echo "--- sitemap.xml ---"
curl -sk $R https://rex.moscow/sitemap.xml -o /tmp/sm2.xml -w 'http=%{http_code} bytes=%{size_download}\n'
cmp -s /tmp/sm1.xml /tmp/sm2.xml && echo "файлы идентичны" || echo "ВНИМАНИЕ: файлы различаются"
echo "--- robots.txt ---"
curl -sk $R https://rex.moscow/robots.txt | grep -i sitemap
echo "--- редиректы ---"
for u in /product/reks-sil /category/gidroizolyaciya /shop/ /index.html /cart-2 /calculators /hacut-ochistitel-2; do
  code=$(curl -sk $R -o /dev/null -w '%{http_code} -> %{redirect_url}' "https://rex.moscow$u")
  echo "  $u : $code"
done
echo "--- http и www ---"
curl -s -o /dev/null -w '  http://rex.moscow/sitemap_index.xml : %{http_code} -> %{redirect_url}\n' http://rex.moscow/sitemap_index.xml
curl -sk --resolve www.rex.moscow:443:127.0.0.1 -o /dev/null -w '  https://www.rex.moscow/ : %{http_code} -> %{redirect_url}\n' https://www.rex.moscow/
echo "--- выборка страниц из sitemap ---"
for u in / /shop /reks-sil /blog /kalkulyatory /kontakty /gidroshponki; do
  code=$(curl -sk $R -o /dev/null -w '%{http_code}' "https://rex.moscow$u")
  echo "  $u : $code"
done
rm -f /tmp/sm1.xml /tmp/sm2.xml

cd /var/www/sites
last=$(ls -d rex.moscow.old-* | sort | tail -1)
for d in rex.moscow.old-*; do [ "$d" = "$last" ] && continue; rm -rf "$d"; echo "удалён резерв: $d"; done
rm -f /tmp/rex-*.tar.gz /tmp/rex-deploy.sh
df -h /var | tail -1
