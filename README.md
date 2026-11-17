# Districts OSM Service

FastAPI-сервис определения района города по координатам. Границы городов и
районов лениво загружаются из OpenStreetMap (Overpass API), хранятся в
PostgreSQL/PostGIS, а список городов и районов кешируется в Redis.

## Возможности

- `GET /districts/resolve` — определить район по точке (`contains` либо
  `nearest` с расстоянием до границы).
- `GET /districts/cities` — города с районами (из Redis-кеша).
- `GET /districts/cities/list` — все города с координатами центра.
- Ленивая автозагрузка города и районов из OSM при первом обращении.
- PostGIS-геометрия `MultiPolygon`/`Point` в WGS84 (`srid=4326`), GiST-индекс.
- Redis-кеш одним JSON-ключом `geo:cities_districts_json`.
- Prometheus-метрики (`/metrics`), health-check (`/health`), опциональный
  OpenTelemetry-трейсинг.

## HTTP API

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/districts/resolve` | Район по `lat`, `lon`, `city_code`; опционально `city_name`, `fallback_nearest` |
| `GET` | `/districts/cities` | Словарь `city_code -> [районы]` |
| `GET` | `/districts/cities/list` | Список городов с координатами центра |
| `GET` | `/health` | 204, если сервис поднялся |
| `GET` | `/metrics` | Prometheus-метрики |

Формат ошибок districts-ручек:

```json
{"error": "district_not_found", "detail": "..."}
```

| Ситуация | Статус | `error` |
|---|---|---|
| Невалидные координаты | 400 | `invalid_coords` |
| Город не найден и автозагрузка не удалась | 404 | `city_not_found` |
| Район не найден | 404 | `district_not_found` |
| Ошибка загрузки из OSM | 502 | `osm_load_failed` |

## Автозагрузка из OSM

Логика запускается из `resolve_district`, если города нет в БД или у него нет
районов:

1. Поиск relations с `boundary=administrative`:
   - Москва и Санкт-Петербург — `admin_level=5`;
   - остальные города — `admin_level=9` (парсер принимает также `10`).
2. Если районы не найдены — фолбек на границу города
   (`place=city` либо `boundary=administrative` + `admin_level=6`), город
   сохраняется как один район.
3. Геометрия собирается из `outer` ways: `linemerge` → `polygonize` →
   `unary_union`, затем `buffer(0)` и приведение к `MultiPolygon`.
4. Названия районов нормализуются (убираются «район», «административный
   округ» и т.п.); район, совпадающий с названием города, пропускается.
5. После успешной загрузки инвалидируется Redis-кеш.

Защита от шторма запросов:

- на каждый город — свой `asyncio.Lock`;
- после неудачи — cooldown `AUTOLOAD_COOLDOWN_SECONDS` (по умолчанию 300 с);
- общий лимитер Overpass — `OVERPASS_RPS_LIMIT` (по умолчанию 1 запрос/с);
- повторные попытки при таймауте/сетевой ошибке/5xx —
  `OVERPASS_RETRY_ATTEMPTS` с экспоненциальным backoff от
  `OVERPASS_RETRY_BACKOFF_S`.

## Схема БД

Таблицы создаются на старте через `Base.metadata.create_all`.

- `citys` — `id UUID PK`, `code` (unique), `name`, `center Point(4326)`,
  `source`, `created_at`, `updated_at`.
- `districts` — `id UUID PK`, `city_id UUID FK -> citys.id ON DELETE CASCADE`,
  `name`, `osm_relation_id`, `polygon MultiPolygon(4326)`,
  `center Point(4326)`, `source`, `created_at`, `updated_at`.
- Индексы: GiST по `districts.polygon`, btree по `districts.city_id`.

Поиск района: `ST_Covers(polygon, point)`. Если точка вне всех районов —
`ST_Distance` в географии, порог `NEAREST_MAX_DISTANCE_M` (5000 м).

## Структура

```
src/
  app.py                 # create_app + lifespan (БД, Overpass, Redis)
  main.py                # запуск uvicorn
  routers.py             # health + districts
  middleware.py          # метрики, CORS, лог запросов
  exc_handler.py         # общий обработчик исключений
  config/                # настройки приложения, лог, трейсинг
  districts/             # роутер, сервис, исключения, автозагрузка
  external/overpass/     # клиент Overpass, QL-запросы, парсеры геометрии
  external/cache/        # Redis-кеш городов и районов
  database/              # модели, репозитории, схемы, подключение
```

## Конфигурация

Все настройки читаются из `.env` (шаблон — `.env.example`). Ключевые группы:

- `DB_*` — PostgreSQL/PostGIS. Для локального compose
  `DB_SSL_ENABLED=false`; при внешней БД с TLS включите SSL и при
  необходимости укажите CA/сертификаты.
- `CACHE_*` — Redis. `CACHE_KEY_PREFIX` задаёт префикс ключа (по умолчанию
  `geo`).
- `OVERPASS_*` — адрес, таймаут, RPS-лимит и retry-политика.
- `NEAREST_MAX_DISTANCE_M` — максимальное расстояние для nearest-фолбека.
- `AUTOLOAD_COOLDOWN_SECONDS` — пауза после неудачной автозагрузки.
- `LOG_*`, `HOST`, `PORT`, `UC_LOG_LEVEL` — логирование и uvicorn.
- `OTEL_*` — трейсинг; по умолчанию отключён (`OTEL_SDK_DISABLED=true`).

## Локальный запуск

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python src/main.py
```

Для локального запуска нужны PostgreSQL с PostGIS и Redis (см. compose).

## Docker

```sh
docker compose up -d --build
docker compose logs -f backend
docker compose down
```

Compose поднимает:

- `backend` на `localhost:8000`;
- `postgres` (образ `postgis/postgis:16-3.4`) на `localhost:55433`;
- `redis` (образ `redis:7-alpine`).

Внутри compose `DB_HOST=postgres` и `CACHE_HOST=redis` переопределяются
автоматически, поэтому в `.env` можно оставить `localhost` для запуска без
Docker.

## Проверки

```sh
ruff check .
ruff format --check .
mypy src
pytest tests/unit
pytest tests/integrations
pre-commit run --all-files
pre-commit run --hook-stage pre-push --all-files
```

`ruff`, `ruff-format` и базовые проверки запускаются на `git commit`;
`mypy` и unit-тесты — на `git push`.

## Ограничения

- Схема БД создаётся через `create_all`, миграций (alembic) пока нет.
- Автозагрузка зависит от доступности Overpass API; при его недоступности
  ручка вернёт `502 osm_load_failed`, сервис продолжит работать.
- Кеш хранит один общий JSON: инвалидация перезаписывает его целиком.
- Районы загружаются только для городов, перечисленных в запросах; фоновой
  синхронизации нет.
