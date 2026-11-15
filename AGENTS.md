# AGENTS.md — rm-catalog

Статический сайт-каталог **инженерной химии РЕКС®** (гидроизоляция, ремонт, защита,
промышленные полы, клеевые системы, анкеровка). Сайт официального дилера завода.

- Прод: **https://rex.moscow** (nginx, `168.113.186.217`, HTTP/2, Let's Encrypt до 08.02.2027).
- Объём: **198 позиций каталога**, 37 разделов, 75 статей, 30 калькуляторов, 6 служебных страниц,
  **351 URL в sitemap**, 633 файла в сборке, ~19 МБ (из них 6 МБ — фото WebP).
- Генератор: Python 3 без фреймворка, HTML собирается строками из `site/*.py`.
- URL повторяют архив WordPress один-в-один (плоские `.html`, без слешей).
- **SEO**: JSON-LD на всех страницах (`site/schema.py`), `lastmod` в sitemap, метатеги
  собираются нормализаторами `product_title()` / `cat_title()` / `trim_desc()`.
  Аудит и замеры — `SEO-AUDIT.md`, `tools/seo_audit.py`, `tools/seo_live.py`.
- **Позиционирование: официальный дилер завода РЕКС** (не производитель). Формулировки —
  «прямые поставки с завода», «официальный дилер», «склад в Наро-Фоминском районе Подмосковья».
  Нельзя писать «наш завод», «мы производим».
- **«ТД РЕКС» / «Торговый дом РЕКС» / ООО «ТД РЕКС» на сайте не упоминаем** — это торговая
  компания завода, а не заказчик. **Данные юрлица заказчика не публикуются вообще, пока он их
  не подтвердит**: `C.LEGAL` и `C.REQUISITES` пустые, в подвале «© 2014–2026. Информация на сайте
  не является публичной офертой», строки «Реквизиты» на контактах нет, `legalName` в JSON-LD
  не выводим. Когда клиент даст название юрлица и реквизиты — заполнить `LEGAL`/`REQUISITES`
  в `site/config.py` и вернуть `legalName` в `schema.org()`.

## Контакты (как на старом сайте, `site/config.py`)

| Поле | Значение |
|---|---|
| Телефон | `+7 (495) 155-01-31` (`PHONE`, `PHONE_HREF`) |
| Почта | `info@rex.moscow` |
| Адрес | Московская обл., г. Наро-Фоминск, Московская ул., 15 (`ADDR`) |
| Второй адрес | г. Феодосия, ул. Чехова, 5 (`ADDR_2`, подпись — `ADDR_2_LABEL`) |
| Часы | Пн–Пт 9:00–18:00 (`HOURS`) |
| Статус | Официальный дилер завода РЕКС (`DEALER`) |
| Выезд | `VISIT_TITLE`, `VISIT_LEAD`, `VISIT_URL` — бесплатно по Москве и Подмосковью |

В прайсе для менеджеров указан другой номер — (495) 647-14-79 и адрес пр-т Маршала Жукова,
2/2/1, оф. 508. На сайте стоят контакты старого сайта; менять только по решению клиента.


## Структура проекта

```
E:\Сайты\rex.moscow\
├─ AGENTS.md                  этот файл
├─ STATUS.md                  история: паритет URL, состояние сайтов
├─ site\                      генератор
│  ├─ build.py                точка входа: собирает dist, sitemap, поиск, robots, og
│  ├─ config.py               BASE, контакты, разделы, факты, нормативы
│  ├─ shell.py                head/header/footer, цена, формы, CTA
│  ├─ pages.py                все страницы: главная, каталог, карточка, блог, калькуляторы
│  ├─ content.py              тексты: кластеры, FAQ, страницы, статьи
│  ├─ images.py               фото товаров и обложки статей из data/images.json
│  ├─ schema.py               JSON-LD: Organization, WebSite, Product, BreadcrumbList, Article, FAQ
│  ├─ kb.py                   факты завода reks.pro для карточек (data\rekspro\kb.json)
│  └─ art.py                  параметрические SVG-«пластины» упаковки и hero-чертёж
├─ assets\                    site.css, site.js, fonts\ (woff2), img\p и img\a (WebP)
├─ data\
│  ├─ model.json              модель сайта: products, cats, pages, posts, calcs
│  ├─ model.backup.json       создаётся автоматически перед правкой цен
│  ├─ prices.json             разобранный прайс-лист (4 уровня цен)
│  ├─ images.json             манифест фото: slug -> webp
│  ├─ price_sync.json         «было/стало» последнего обновления цен
│  ├─ rekspro\                данные завода: pages.jsonl, kb.json, match.json, manual_match.json,
│  │                          img\ (фото), images.jsonl; raw\ — исходные страницы reks.pro
│  └─ prices_prev_snapshot.json  снимок старых цен из dist (для диффов)
├─ Прайс-лист ТД РЕКС_*.xlsx  исходный прайс (файл так назван поставщиком; parse_price.py
│                             берёт его из корня)
├─ missing-images-rex.csv     товары без фото (генерируется missing_images.py)
├─ mapping.md                 карта «карточка сайта → строка прайса» (export_mapping.py)
├─ unpublished\               неопубликованные материалы из дампа БД (export_unpublished.py)
├─ tools\                     служебные скрипты (см. ниже)
├─ deploy\                    скрипты деплоя, server.env (доступ), архив сборки;
│                             new-server\ — незапущенный вариант под 109.95.77.86 (IIS + certs)
├─ dist\                      результат сборки (= корень сайта на сервере)
├─ dist_nginx\                vhost'ы, web.config для IIS, rex-redirects.txt
└─ shots\                     скриншоты дизайна (не влияют на сборку)
```

## Команды

```powershell
$py = 'C:\Users\Кирилл\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
cd E:\Сайты\rex.moscow

& $py site\build.py          # сборка dist (~1 c)
& $py tools\links.py         # проверка внутренних ссылок: должно быть broken: 0
& $py tools\serve_local.py   # локальный сервер http://127.0.0.1:8090
& $py tools\parity.py        # сверка с архивными URL (см. STATUS.md)
& $py tools\make_images.py   # фото из бэкапа -> assets\img\*.webp (Pillow)
& $py tools\missing_images.py    # -> missing-images-rex.csv (товары без фото)
& $py tools\export_unpublished.py # -> unpublished\ (черновики и запланированные из дампа БД)
& $py tools\extract_dates.py      # даты статей из БД -> data\post_dates.json
& $py tools\seo_audit.py          # SEO-аудит сборки: мета, дубли, JSON-LD, sitemap, похожесть
& $py tools\seo_live.py           # живые проверки: редиректы, сжатие, Core Web Vitals
& $py tools\build_price_map.py    # автодополнение карты «карточка -> строка прайса» (--apply)
& $py tools\export_mapping.py     # -> mapping.md: полная карта соответствия прайсу
```

Обновление цен — отдельная процедура, см. «Прайс и цены» ниже.

### База знаний завода (описания товаров и статей)

Описания карточек и вставки в статьи собираются из фактов официального сайта завода
**reks.pro**. Цепочка скриптов (на хосте нужен Python 3.13 с `bs4`, `PyMuPDF`, `Pillow`):

```powershell
$py13 = 'C:\Users\Кирилл\AppData\Local\Programs\Python\Python313\python.exe'
& $py13 tools\rekspro_crawl.py     # sitemap reks.pro -> data\rekspro\pages.jsonl (+ raw\)
& $py13 tools\rekspro_assets.py    # фото -> data\rekspro\img, PDF -> Knowledge\reks.pro\pdf, текст
& $py13 tools\build_kb_rekspro.py  # -> E:\Оптимизация\Knowledge\reks.pro + data\rekspro\kb.json
& $py13 tools\rekspro_match.py     # пары «карточка сайта -> карточка завода» -> match.json
& $py  tools\rekspro_images.py     # фото завода -> assets\img\p\<slug>.webp (900 px, WebP)
& $py  tools\articles_enrich.py    # вычитка статей + блок «Материалы завода по теме»
& $py  tools\articles_check.py     # отчёт по типографике, повторам, дублям предложений
& $py  tools\build_kb_rekspro.py   # повторить после смены PDF/фото
```

- `site/kb.py` отдаёт факты карточке: `kb.facts(slug)` → `intro`, `app`, `adv`, `kv`,
  `pack`, `cons`, `prep`, `mix`, `apply`, `pdf`. `site/content.py` строит из них тело
  карточки (`_facts_text`), мета-описание — оттуда же (`ct["meta"]`).
- Ручные пары и исключения — `data\rekspro\manual_match.json` (значение `null` = у завода
  карточки нет, остаётся шаблонный текст кластера).
- Правило: **любая цифра в тексте должна иметь источник в базе знаний**. Нет в базе — не пишем.
- Фото завода уже WebP, пережимаются в 900 px / q82 и кладутся в общий манифест
  `data\images.json`; приоритет у фото из бэкапа старого сайта.

## Деплой

Атомарная подмена каталога, без простоя:

1. `tar -czf deploy\dist-new.tar.gz -C dist .`
2. `pscp deploy\dist-new.tar.gz root@168.113.186.217:/tmp/rex-<TS>.tar.gz`
3. правим `TS` в `deploy\remote_deploy.sh`, запускаем:
   `plink -batch -ssh -hostkey <hostkey> -pw <pw> -m deploy\remote_deploy.sh root@168.113.186.217`

Скрипт распаковывает в `/var/www/sites/.rex-new-<TS>`, делает `chown www-data`,
переименовывает текущий каталог в `rex.moscow.old-<TS>`, ставит новый, проверяет `nginx -t`
и перезагружает nginx. Откат — обратным `mv`.

Старые бэкапы чистим: `deploy\remote_cleanup.sh` оставляет только последний.

## Сервер

| Параметр | Значение |
|---|---|
| Хост | `168.113.186.217` (`kirill6.fvds.ru`) |
| Пользователь | `root`, доступ по паролю (см. `deploy\server.env`) |
| Host key | `SHA256:Q+u95C//yvLTCRkp/d8MjEDUJxN9SNXJdM8jFnRVh0s` |
| Корень сайта | `/var/www/sites/rex.moscow` |
| Vhost | `/etc/nginx/sites-available/delivery-rex.moscow.conf` (80 → 301) и `delivery-rex.moscow-ssl.conf` (443) |
| Сертификат | `/etc/letsencrypt/live/rex.moscow/`, продление через deploy-hook `reload-nginx.sh` |
| Резерв | `/var/www/sites/rex.moscow.old-<TS>` (последний) |
| Диск | 79 ГБ, занято 76 % |

Рядом на том же сервере живут десятки других сайтов — **не трогать чужие каталоги и vhost'ы**,
не делать `nginx -s stop`, только `systemctl reload nginx`.

## Модель данных

`data/model.json`:

- `products[]` — `id, slug, name, cats[], price, old, sku, short, desc, img, meta_title, meta_desc,
  pack, unit, price_level, price_date`
- `cats[]` — `id, slug, name, parent, count, meta_title, meta_desc, desc`
- `pages[]` — служебные страницы из архива (`slug`, `title`, `content` в разметке WP)
- `posts[]` — 75 статей (`title, slug, category, content_len, …`)
- `calcs[]` — 30 калькуляторов (метаданные), формулы и поля — в `site/pages.py` / `site/content.py`

Структура каталога (6 направлений) задана в `site/config.py` → `GROUPS`.

## Прайс и цены

Источник — дистрибьюторский прайс завода (xlsx так назван поставщиком: «Прайс-лист ТД РЕКС_…»;
4 листа: РиЗБ, комплектующие хим. анкеров, инъекции, гидролента). Действующая версия:
**с 10.09.2026, цены с НДС**. Название файла — не наше имя, на сайте оно не встречается.

| Уровень | Медианная скидка |
|---|---|
| Розница («ЦЕНА реализации») | — (публикуется на сайте) |
| от 3 т | −5 % |
| от 10 т (СТОП-цена) | −9…−13 % |
| Дистрибьютор | −23,5…−28,5 % |

Процедура обновления:

```powershell
& $py tools\parse_price.py        # xlsx -> data\prices.json (положите новый xlsx в корень)
& $py tools\apply_prices.py       # prices.json -> model.json: price, pack, unit, meta_title
& $py site\build.py
& $py tools\price_report.py       # отчёт «было/стало» -> data\price_sync.json
& $py tools\export_knowledge.py   # CSV в E:\Оптимизация\Knowledge\rex.moscow
& $py tools\export_knowledge_md.py
```

Сопоставление «карточка сайта → строка прайса» — словарь `MAP` в `tools\apply_prices.py`:
`"slug": (лист, номер строки в xlsx, номер варианта упаковки)` плюс `data\price_map_auto.json`
(точные совпадения названий и размеров, генерирует `tools\build_price_map.py`).
Сейчас сопоставлено **167 карточек из 198**; полная карта с ценами и фасовками —
**[mapping.md](mapping.md)** (`tools\export_mapping.py`). Позиции прайса без записи в карту
на сайт не попадают. Цена в `<title>` пересобирается там же.

База знаний по прайсу: **`E:\Оптимизация\Knowledge\rex.moscow`** (`README.md`, `price_items.csv`,
`price_tech.csv`, `price_policy.md`, `assortment_gap.md`, `catalog_expansion_2026-11-14.md`,
`site_price_sync_2026-11-14.md`).

## Фотографии

Источник — бэкап взломанного сайта: `D:\Old Sites\rex.moscow\public_html\wp-content\uploads`
(2 300 изображений) и дамп БД `MySQL\odinoknx_rex.sql.gz` (товары, SKU, привязка фото).

- `tools\make_images.py` → `assets\img\p\<slug>.webp` (900 px, q82) и `assets\img\a\<slug>.webp`
  (760×428, q72); манифест — `data\images.json`.
- `tools\match_covers.py` сопоставляет обложки статей с постами (жадное сопоставление по сходству
  слагов), `tools\scan_uploads.py` — свободные изображения, `tools\parse_db.py` — разбор дампа.
- На сайте: фото товара в карточке каталога (`pcard__plate--photo`), в карточке товара — фото +
  маленькая пластина-схема; для статей — обложка в списке блога и в шапке статьи.
- **Все изображения только WebP**; исходные jpg/png в сборку не попадают.
- Если фото нет — рисуется параметрическая пластина (`site/art.py`); для анкерных шпилек —
  отдельный чертёж стержня с резьбой и размером (`_stud`).

## Дизайн-система

«Технический паспорт / чертёж», светлая голубая схема (фирменный стиль РЕКС, утверждён клиентом):

- `--acc: #0088cc` (акцент), `--paper: #f2f8fc`, `--ink: #0d2b3e`, линии `#a9c9e0`.
- Шрифты: **Geologica** (заголовки), **Commissioner** (текст), **IBM Plex Mono** (данные),
  self-hosted woff2 в `assets\fonts`.
- Каждый товар получает параметрический SVG-«пластину» упаковки (`site/art.py`,
  типы: bag / pail / canister / cartridge / roll / profile / drum / stud).
- **Иконки** — `site/art.py` → `ICONS` + `icon(name, cls)`: 20+ штриховых иконок 24×24
  (толщина 1.5, `currentColor`) в стиле чертежа. Есть `helmet` (выезд специалиста), `drop`,
  `trowel`, `layers`, `shield`, `glue`, `bolt`, `warehouse`, `truck`, `factory`, `ruler`,
  `seal`, `package`, `tag`, `chat`, `doc`, `calc`, `phone`, `mail`, `pin`, `clock`.
  Применяются в шапке, карточках направлений, паспортных строках, калькуляторах, подвале.
  Добавляя иконку — рисовать под сетку 24×24 и проверять в 14–22 px.
- Плотная сетка, моно-подписи, «паспортные» таблицы характеристик, никаких стоковых фото.

## Правила

1. **URL не меняем.** Плоские `<slug>.html`, ссылки без завершающего слеша; редиректы
   (`/product/*`, `/category/*`, `/cart-2`, `/shop/page/N`) — в `dist_nginx\delivery-rex.moscow-ssl.conf`.
2. Меняя `site.css`/`site.js`, поднимаем `?v=` в `site/shell.py` — иначе посетители увидят кэш.
3. Тексты и данные — по-русски, инженерный тон, без маркетингового шума и без выдуманных цифр.
4. Цены — только из прайса; «по запросу» остаётся там, где позиции нет в прайсе.
5. Все правки — в `site/`, `assets/`, `data/`; `dist/` пересобирается, руками не правится.
6. Перед деплоем: `build.py` → `links.py` (0 битых) → проверка 2–3 страниц локально.
7. **Кнопка «Вызвать специалиста на объект» — на всех страницах, кроме гидрошпонок.** Она есть
   в верхней строке, мобильном меню, подвале (`shell.topbar/header/footer` с флагом `no_visit`)
   и отдельной полосой `shell.visit_cta()`. Для гидрошпонок (категория `gidroshponki`, её
   подразделы и 8 карточек) передаём `no_visit=True`: список исключений — `C.VISIT_EXCEPT`.
8. **Не добавляем выдуманных контактов и цифр.** Телефон/адрес/часы — только из `config.py`,
   цены — только из прайса.
9. **Метаданные не пишем руками.** `title` — через `product_title()` / `cat_title()` (≤ 70 знаков),
   `description` — через `trim_desc()` (≤ 175, по границе предложения), дубли описаний
   отслеживает `Model.desc_owner`. Новую страницу подключаем к `schema.dumps(...)`, иначе
   она останется без разметки (проверяется `tools\seo_audit.py`).
10. **Удаляя страницу, ставим 301.** Товар или раздел, ушедший с сайта, получает `rewrite`
    в `dist_nginx\delivery-rex.moscow-ssl.conf` и строку в `rex-redirects.txt`
    (см. пример `/hacut-ochistitel-2`).

## Подводные камни

- **PowerShell + кириллические пути + inline python** — источник постоянных ошибок квотинга.
  Любой нетривиальный код писать в файл и запускать `& $py file.py`, а не `-c "..."`.
- **НЕЛЬЗЯ править файлы проекта через `(Get-Content -Raw) ... | Set-Content`.** В PowerShell 5.1
  `Get-Content` без `-Encoding` читает UTF-8 как ANSI, и кириллица превращается в «РЎС‚СЂР°РЅРёС†Р°».
  Правки — только инструментом `edit`/`write`. Если такое случилось, спасает
  `tools\fix_encoding.py` (обратное преобразование UTF-8 → CP1251-байты → UTF-8).
- **plink/pscp**: команды передавать файлом (`plink -m script.sh`), а не строкой — иначе `|`, `$`,
  кавычки ломаются. `nginx -t` пишет warnings в stderr → plink вернёт код 1, это нормально.
- **.sh для сервера — только LF.** Файлы создаём в UTF-8 без BOM.
- `dist\` на сервере — это и есть `/var/www/sites/rex.moscow`, никакого `public/` внутри.
- Не удалять каталог сайта до переключения DNS/проверки: сначала `mv`, потом проверка, потом чистка.
- Порт 80 в vhost'е только редиректит на https — локальные проверки делать с `Host: rex.moscow`.

## Что ждёт решения клиента

1. **Контакты поставлены как на старом сайте**: `+7 (495) 155-01-31`, Московская обл.,
   г. Наро-Фоминск, Московская ул., 15, г. Феодосия, ул. Чехова, 5, Пн–Пт 9:00–18:00.
   В прайсе другие данные — (495) 647-14-79, пр-т Маршала Жукова, 2, корп. 2, стр. 1, оф. 508.
   Если менеджеры работают с московского офиса, поменять `PHONE`, `PHONE_HREF`, `ADDR`,
   `ADDR_2`, `ADDR_2_LABEL`, `HOURS` в `site\config.py`.
2. **Четыре позиции** после сверки с прайсом подешевели на 30–47 % (СИЛ, Акрилик Эласт ВН,
   Фикс Акрэп, ПЛАГ) — нужна сверка с 1С: старые цены могли включать наценку.
3. **Гидрошпонки, мембрана, клеевые смеси, огнезащита, НП 3000/4000, TEKASIL** есть в каталоге,
   но отсутствуют в этом прайсе — цены «по запросу», нужны прайсы других направлений.
4. Цветовые варианты (белый/серый/красный) выведены отдельными карточками — можно объединить
   переключателем цвета, если так удобнее клиенту.
5. **43 позиции без фото** (`missing-images-rex.csv`): 33 анкерные шпильки SKA, 4 гильзы,
   насадка, часть гидрошпонок и МСЦ. Для них рисуется схема-пластина; фото у завода на сайте
   нет (страницы-заглушки), нужны снимки упаковки от клиента или из 1С.
6. **Отложенная публикация статей** — механизм описан в `unpublished\README.md`, включается
   по решению клиента (сейчас в бэкапе неопубликованных статей нет).

## Связанные папки

| Путь | Что там |
|---|---|
| `E:\Оптимизация\Knowledge\rex.moscow` | база знаний по прайсу, ценам и каталогу |
| `E:\Оптимизация\Knowledge\reks.pro` | **база знаний завода**: карточки, характеристики, PDF и их распознанный текст, статьи, услуги — источник описаний и фактов |
| `D:\Old Sites\rex.moscow` | бэкап старого сайта: `wp-content\uploads` + `MySQL\odinoknx_rex.sql.gz` |
| `E:\Design\rex_audit\cdx_rex_moscow.json` | CDX-выгрузка веб-архива (паритет URL) |
| `E:\Оптимизация\Rex.moscow` | исходные данные прошлого проекта (products/categories/pages) |
| `E:\Design\rex` | прежнее расположение проекта (основные файлы перенесены сюда) |
