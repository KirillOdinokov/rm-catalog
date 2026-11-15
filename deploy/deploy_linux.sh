#!/bin/sh
# Деплой rex.moscow с flux-сервера: tar dist -> scp на enixfirstvds -> атомарная подмена.
# Запуск: sh deploy/deploy_linux.sh
set -e
TS=$(date +%Y%m%d-%H%M)
cd "$(dirname "$0")/.."

tar -czf /tmp/rex-$TS.tar.gz -C dist .
scp /tmp/rex-$TS.tar.gz enixfirstvds:/tmp/rex-$TS.tar.gz

ssh enixfirstvds "TS=$TS sh -s" <<'REMOTE'
set -e
SITE=/var/www/sites/rex.moscow
NEW=/var/www/sites/.rex-new-$TS
TAR=/tmp/rex-$TS.tar.gz
test -f "$TAR" || { echo "нет файла $TAR"; exit 1; }
rm -rf "$NEW"
mkdir -p "$NEW"
tar -xzf "$TAR" -C "$NEW"
chown -R www-data:www-data "$NEW"
chmod -R u+rwX,go+rX,go-w "$NEW"
if [ -d "$SITE" ]; then mv "$SITE" "$SITE.old-$TS"; fi
mv "$NEW" "$SITE"
nginx -t 2>&1 | tail -2
systemctl reload nginx
echo "deployed $TS"
REMOTE

rm -f /tmp/rex-$TS.tar.gz
echo "done $TS"
