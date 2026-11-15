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

# 3) сборка + деплой при изменении
if [ "$changed" != "0" ]; then
  echo "changed=$changed -> build + deploy" >> "$LOG"
  $PY site/build.py >> "$LOG" 2>&1
  sh deploy/deploy_linux.sh >> "$LOG" 2>&1
fi
