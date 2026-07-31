# Corp Portal

Django-портал для каталога, базы знаний, новостей, акций и Telegram-бота.

## Локальный запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Для импорта презентаций с OCR на Windows нужен Tesseract. В Docker-образе он ставится автоматически.

## Деплой

Проект подготовлен для VPS/VDS через Docker Compose:

- `Dockerfile` - образ Django/Gunicorn с Tesseract OCR.
- `compose.yaml` - PostgreSQL, web-приложение и Caddy с HTTPS.
- `promotion_sync` - автоматический импорт активных источников акций раз в час.
- `deploy/Caddyfile` - reverse proxy для домена.
- `.env.production.example` - шаблон production-переменных.
- `deploy/HOSTER_BY.md` - пошаговая инструкция для hoster.by.

Минимальная команда на сервере после настройки `.env.production`:

```bash
docker compose --env-file .env.production up -d --build
```

Интервал импорта акций задаётся переменной `PROMOTION_SYNC_INTERVAL_SECONDS`
(по умолчанию `3600`, минимум `60`). Проверить импорт вручную без записи можно так:

```bash
docker compose --env-file .env.production exec web python manage.py sync_promotion_sources --dry-run
```

В админке у каждого источника задаются два предохранителя: минимальное число
распознанных акций и максимальная доля строк, которая может исчезнуть за один
импорт. Подозрительно пустая выгрузка останавливается до любых изменений.
Все успешные проверки, импорты и ошибки сохраняются в разделе «История импорта
акций» вместе со счётчиками и длительностью запуска.
