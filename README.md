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
- `deploy/Caddyfile` - reverse proxy для домена.
- `.env.production.example` - шаблон production-переменных.
- `deploy/HOSTER_BY.md` - пошаговая инструкция для hoster.by.

Минимальная команда на сервере после настройки `.env.production`:

```bash
docker compose --env-file .env.production up -d --build
```
