#!/bin/sh
# Уборка старых бэкапов rex.moscow на сервере: оставляем только последний.
ls -d /var/www/sites/rex.moscow.old-* 2>/dev/null
echo "--- удаляем всё, кроме последнего ---"
last=$(ls -1d /var/www/sites/rex.moscow.old-* 2>/dev/null | sort | tail -1)
for d in $(ls -1d /var/www/sites/rex.moscow.old-* 2>/dev/null | sort); do
  if [ "$d" != "$last" ]; then
    rm -rf "$d"
    echo "удалён $d"
  fi
done
echo "--- осталось ---"
ls -1d /var/www/sites/rex.moscow* 2>/dev/null
df -h /var | tail -1
