#!/bin/sh
# Оркестрация на flux: подтянуть код из git -> sync цен из Базы -> при изменении build + deploy.
# Пути — под flux-сервер (/home/kirill/...). На локальной машине не запускать.
cd /home/kirill/rex.moscow

# 1) код из git (сбрасываем локальные правки цен в model.json — их пересоздаст sync)
git checkout -- data/model.json 2>/dev/null
git pull --ff-only -q origin main 2>&1 | tail -2

export REX_API_URL="http://127.0.0.1:8001/api/site/6/prices"
PY=/home/kirill/flux/.venv/bin/python
LOG=/tmp/rex_sync.log

# 2) цены из Базы
$PY tools/sync_prices.py > "$LOG" 2>&1
changed=$($PY -c "import json; print(len(json.load(open('data/price_sync.json', encoding='utf-8'))['changed']))" 2>/dev/null || echo 0)

# 2б) отложенная публикация: статьи, чей publish_at наступил, но которых ещё нет в dist
publish_due=$($PY tools/check_publish_due.py 2>/dev/null || echo 0)
publish_json=/tmp/rex_publish_due.json
rm -f "$publish_json"
if [ "$publish_due" != "0" ]; then
  $PY tools/check_publish_due.py --json > "$publish_json" 2>/dev/null || true
fi

# 3) сборка + деплой при изменении цен ИЛИ наступившей публикации
if [ "$changed" != "0" ] || [ "$publish_due" != "0" ]; then
  echo "changed=$changed publish_due=$publish_due -> build + deploy" >> "$LOG"
  if $PY site/build.py >> "$LOG" 2>&1 && sh deploy/deploy_linux.sh >> "$LOG" 2>&1; then
    # уведомление в «Базу» о вышедших статьях (колокольчик в веб-интерфейсе)
    if [ "$publish_due" != "0" ] && [ -s "$publish_json" ]; then
      NOTIFY_KEY=$(grep -m1 '^METRICS_KEY=' /home/kirill/flux/.env 2>/dev/null | cut -d= -f2- | tr -d '"')
      if [ -n "$NOTIFY_KEY" ]; then
        BASE_NOTIFY_URL="http://127.0.0.1:8001/api/site/events" \
        BASE_NOTIFY_KEY="$NOTIFY_KEY" \
          $PY tools/notify_published.py --file "$publish_json" --site-id 6 >> "$LOG" 2>&1
      fi
    fi
  fi
fi
