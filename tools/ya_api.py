# -*- coding: utf-8 -*-
"""OAuth-токен Яндекса и проверка доступа к API Метрики и Вебмастера.

Доступы лежат в deploy/yandex-oauth.env (в git не попадает):
    CLIENT_ID / CLIENT_SECRET — из https://oauth.yandex.ru/client/<id>
    METRIKA_ID, WEBMASTER_HOST — для проверок

Как получить токен (один раз, дальше хватает refresh_token):

    python tools/ya_api.py --url          # печатает ссылку для браузера
    ...открыли ссылку, вошли под нужным аккаунтом Яндекса, нажали «Разрешить»...
    ...Яндекс показал код на странице verification_code (или редиректнул со ?code=...)
    python tools/ya_api.py --code XXXXXX  # можно вставить как код, так и всю ссылку
    python tools/ya_api.py --login        # проверка: счётчики Метрики + хосты Вебмастера
    python tools/ya_api.py --refresh      # если токен истёк/отозван

Токен сохраняется в deploy/yandex-token.json (тоже в .gitignore).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE, "deploy", "yandex-oauth.env")
TOKEN_PATH = os.path.join(BASE, "deploy", "yandex-token.json")

AUTHORIZE = "https://oauth.yandex.ru/authorize"
TOKEN_URL = "https://oauth.yandex.ru/token"
# для приложений «Для доступа к API» redirect_uri зашит на эту страницу
REDIRECT_URI = "https://oauth.yandex.ru/verification_code"
METRIKA_API = "https://api-metrika.yandex.net"
WEBMASTER_API = "https://api.webmaster.yandex.net/v4"


def load_env(path=ENV_PATH):
    cfg = {}
    if not os.path.exists(path):
        sys.exit("нет файла доступов: %s" % path)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def authorize_url(client_id):
    return "%s?%s" % (AUTHORIZE, urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "force_confirm": "yes",          # всегда показывать экран разрешений
    }))


def extract_code(raw):
    """Принимает и код, и полную ссылку вида ...?code=1234567 или #code=."""
    raw = raw.strip()
    if raw.lower().startswith("http") or "code=" in raw:
        q = urllib.parse.urlparse(raw.replace("#", "?"))
        for part in (q.query, q.fragment):
            vals = urllib.parse.parse_qs(part)
            if vals.get("code"):
                return vals["code"][0]
        sys.exit("в ссылке нет параметра code: %s" % raw)
    return raw


def post_form(url, data):
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "rex.moscow-tools/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "replace")))


def save_token(tok):
    tok = dict(tok)
    tok["obtained_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if tok.get("expires_in"):
        tok["expires_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%S%z", time.localtime(time.time() + int(tok["expires_in"])))
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, "w", encoding="utf-8") as f:
        json.dump(tok, f, ensure_ascii=False, indent=2)
    return tok


def load_token():
    if not os.path.exists(TOKEN_PATH):
        sys.exit("нет токена: %s — сначала --url и --code" % TOKEN_PATH)
    with open(TOKEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_token(cfg):
    """Токен из файла; при отсутствии — понятная подсказка."""
    tok = load_token()
    if not tok.get("access_token"):
        sys.exit("в %s нет access_token" % TOKEN_PATH)
    return tok["access_token"]


def api(url, token, params=None, method="GET", body=None):
    if params:
        url = "%s?%s" % (url, urllib.parse.urlencode(params))
    data = None
    headers = {
        "Authorization": "OAuth %s" % token,
        "User-Agent": "rex.moscow-tools/1.0",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        sys.exit("HTTP %s %s %s\n%s" % (e.code, method, url, text[:800]))


def cmd_url(cfg):
    print("1. Откройте ссылку и войдите тем аккаунтом Яндекса, у которого есть")
    print("   доступ к счётчику %s и к сайту %s:\n" % (cfg.get("METRIKA_ID", "—"),
                                                      cfg.get("WEBMASTER_HOST", "—")))
    print(authorize_url(cfg["CLIENT_ID"]))
    print("\n2. Нажмите «Разрешить». Яндекс покажет код (или вернёт ссылку с ?code=...).")
    print("3. Передайте код скрипту:")
    print("   python tools\\ya_api.py --code <код>")


def cmd_code(cfg, raw):
    code = extract_code(raw)
    print("меняю код на токен...")
    tok = post_form(TOKEN_URL, {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": cfg["CLIENT_ID"],
        "client_secret": cfg["CLIENT_SECRET"],
    })
    if "access_token" not in tok:
        sys.exit("Яндекс не выдал токен: %s" % json.dumps(tok, ensure_ascii=False))
    save_token(tok)
    print("токен сохранён: %s" % TOKEN_PATH)
    print("  scope: %s" % tok.get("scope", "—"))
    print("  живёт: %s c" % tok.get("expires_in", "—"))
    print("  refresh_token: %s" % ("есть" if tok.get("refresh_token") else "нет"))


def cmd_refresh(cfg):
    tok = load_token()
    if not tok.get("refresh_token"):
        sys.exit("в токене нет refresh_token — получите заново через --url и --code")
    print("обновляю по refresh_token...")
    new = post_form(TOKEN_URL, {
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
        "client_id": cfg["CLIENT_ID"],
        "client_secret": cfg["CLIENT_SECRET"],
    })
    if "access_token" not in new:
        sys.exit("не обновился: %s" % json.dumps(new, ensure_ascii=False))
    if not new.get("refresh_token"):
        new["refresh_token"] = tok["refresh_token"]
    save_token(new)
    print("новый токен сохранён, scope: %s" % new.get("scope", "—"))


def cmd_login(cfg):
    token = get_token(cfg)
    print("== Метрика ==")
    data = api(METRIKA_API + "/management/v1/counters", token, {"per_page": 1000})
    counters = data.get("counters", [])
    print("счётчиков доступно: %d" % len(counters))
    for c in counters:
        mark = "  <-- наш" if str(c.get("id")) == str(cfg.get("METRIKA_ID")) else ""
        print("  %-12s %s%s" % (c.get("id"), c.get("name", ""), mark))

    print("\n== Вебмастер ==")
    user = api(WEBMASTER_API + "/user/", token)
    uid = user.get("user_id")
    print("user_id: %s" % uid)
    hosts = api("%s/user/%s/hosts/" % (WEBMASTER_API, uid), token)
    for h in hosts.get("hosts", []):
        print("  %-28s verified=%s" % (h.get("host_id"),
                                       h.get("verification_state", "")))


def cmd_stats(cfg, days):
    token = get_token(cfg)
    cid = cfg.get("METRIKA_ID")
    if not cid:
        sys.exit("в deploy/yandex-oauth.env не задан METRIKA_ID")
    date2 = time.strftime("%Y-%m-%d")
    date1 = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
    data = api(METRIKA_API + "/stat/v1/data", token, {
        "id": cid, "date1": date1, "date2": date2,
        "metrics": "ym:s:visits,ym:s:users,ym:s:pageviews,ym:s:bounceRate",
        "accuracy": "full",
    })
    print("счётчик %s, %s..%s" % (cid, date1, date2))
    for k, v in zip(data.get("query", {}).get("metrics", []),
                    data.get("totals", [0] * 4)):
        print("  %-18s %.1f" % (k, v))


GOALS_JS = [
    ("phone", "Клик по телефону (reachGoal phone)"),
    ("email", "Клик по e-mail (reachGoal email)"),
    ("lead", "Отправка заявки (reachGoal lead)"),
    ("visit", "Вызов специалиста на объект (reachGoal visit)"),
]


def cmd_goals(cfg, create=False):
    token = get_token(cfg)
    cid = cfg.get("METRIKA_ID")
    if not cid:
        sys.exit("в deploy/yandex-oauth.env не задан METRIKA_ID")
    url = "%s/management/v1/counter/%s/goals" % (METRIKA_API, cid)
    data = api(url, token, {"per_page": 200})
    goals = data.get("goals", [])
    have = set()
    print("счётчик %s: целей %d" % (cid, len(goals)))
    for g in goals:
        mark = ""
        if g.get("type") == "action":
            for c in g.get("conditions") or []:
                ident = c.get("url") or ""
                if ident in dict(GOALS_JS):
                    have.add(ident)
                    mark = "  <-- JS-событие"
        print("  %-6s %-12s %-45s%s" % (g.get("id"), g.get("type"),
                                        g.get("name", "")[:45], mark))
    missing = [x for x in GOALS_JS if x[0] not in have]
    if not missing:
        print("\nвсе четыре JS-цели на месте")
        return
    print("\nне хватает: %s" % ", ".join(m[0] for m in missing))
    if not create:
        print("создать: python tools\\ya_api.py --goals-init")
        return
    for ident, name in missing:
        res = api(url, token, method="POST", body={"goal": {
            "name": name,
            "type": "action",
            "conditions": [{"type": "exact", "url": ident}],
            "is_favorite": 0,
        }})
        g = res.get("goal", {})
        print("создана: %-6s %s (%s)" % (g.get("id"), g.get("name"), ident))


def main():
    p = argparse.ArgumentParser(description="Токен и проверки API Яндекса (Метрика, Вебмастер)")
    p.add_argument("--url", action="store_true", help="ссылка для получения кода")
    p.add_argument("--code", help="код из браузера или полная ссылка с ?code=")
    p.add_argument("--refresh", action="store_true", help="обновить токен по refresh_token")
    p.add_argument("--login", action="store_true", help="проверить доступ: счётчики и хосты")
    p.add_argument("--stats", type=int, metavar="DAYS", help="сводка Метрики за N дней")
    p.add_argument("--goals", action="store_true", help="показать цели Метрики")
    p.add_argument("--goals-init", action="store_true", help="создать недостающие JS-цели")
    a = p.parse_args()
    cfg = load_env()
    if a.url:
        cmd_url(cfg)
    elif a.code:
        cmd_code(cfg, a.code)
    elif a.refresh:
        cmd_refresh(cfg)
    elif a.login:
        cmd_login(cfg)
    elif a.stats:
        cmd_stats(cfg, a.stats)
    elif a.goals:
        cmd_goals(cfg)
    elif a.goals_init:
        cmd_goals(cfg, create=True)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
