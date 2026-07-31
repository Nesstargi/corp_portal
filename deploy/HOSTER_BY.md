# Деплой на hoster.by

Инструкция рассчитана на тестовый VPS/VDS с Ubuntu 24.04 LTS и Docker Compose.

## Какой сервер выбрать

Для этого проекта лучше брать не виртуальный хостинг, а VPS/VDS или Cloud VPS с root-доступом. Нужен Docker, PostgreSQL, Caddy и обработка презентаций через Tesseract OCR.

Рекомендуемый тестовый сервер:

- Ubuntu 24.04 LTS.
- 2 vCPU.
- 4 GB RAM.
- 40-60 GB SSD/NVMe.
- 1 публичный IPv4.
- Открытые порты: 22, 80, 443.

Минимум для короткого теста: 1-2 vCPU, 2 GB RAM, 25-30 GB SSD. Но импорт презентаций и OCR могут упираться в память, поэтому 4 GB RAM спокойнее.

## DNS

В панели домена создай A-запись:

```text
@     A     SERVER_IP
www   A     SERVER_IP
```

Если домен будет только без `www`, достаточно первой записи. Перед запуском Caddy дождись, пока домен резолвится на IP сервера.

## Подготовка сервера

Подключись по SSH:

```bash
ssh root@SERVER_IP
```

Установи Docker:

```bash
curl -fsSL https://raw.githubusercontent.com/Nesstargi/corp_portal/main/deploy/bootstrap-ubuntu-docker.sh -o bootstrap-ubuntu-docker.sh
sh bootstrap-ubuntu-docker.sh
```

Если работаешь не под root, после добавления пользователя в группу `docker` перелогинься в SSH.

## Первый запуск

```bash
git clone https://github.com/Nesstargi/corp_portal.git
cd corp_portal
cp .env.production.example .env.production
nano .env.production
```

Обязательно поменяй:

- `DOMAIN` - твой домен.
- `ALLOWED_HOSTS` - твой домен, при необходимости `www`, а также `127.0.0.1,localhost` для Docker healthcheck.
- `CSRF_TRUSTED_ORIGINS` - `https://твой-домен`.
- `SITE_URL` - `https://твой-домен`.
- `POSTGRES_PASSWORD` - длинный пароль.
- `SECRET_KEY` - длинный случайный ключ.
- `TELEGRAM_BOT_TOKEN` и `TELEGRAM_WEBHOOK_SECRET`, если нужен бот.
- `PROMOTION_SYNC_INTERVAL_SECONDS` — период обновления акций из таблицы (по умолчанию 3600 секунд).

Сгенерировать секреты можно так:

```bash
openssl rand -base64 48
```

Запусти проект:

```bash
docker compose --env-file .env.production up -d --build
docker compose --env-file .env.production ps
```

Создай суперпользователя:

```bash
docker compose --env-file .env.production exec web python manage.py createsuperuser
```

Проверка:

```bash
curl -I https://твой-домен/health/
docker compose --env-file .env.production logs -f web
docker compose --env-file .env.production logs -f promotion_sync
```

После первого запуска открой источник акций в админке, настрой минимальное число
распознанных строк и допустимый процент пропавших акций, затем сначала выполни
«Проверить импорт без сохранения». Результаты всех запусков доступны по ссылке
«История запусков» в карточке источника.

## Обновление после нового push

```bash
sh deploy/deploy.sh
```

Скрипт делает `git pull --ff-only` и пересобирает контейнеры.

## Бэкап базы

```bash
sh deploy/backup-postgres.sh
```

Файлы сохраняются в папку `backups/` на сервере. Медиафайлы лежат в Docker volume `media_data`; для тестового хостинга их можно дополнительно копировать через `docker run --rm -v corp_portal_media_data:/data -v "$PWD/backups:/backup" alpine tar czf /backup/media.tar.gz -C /data .`.

## Полезные команды

```bash
docker compose --env-file .env.production logs -f
docker compose --env-file .env.production restart web
docker compose --env-file .env.production exec web python manage.py check
docker compose --env-file .env.production down
```

## Источники

- hoster.by: https://hoster.by/
- Docker Engine для Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- Docker Compose и `--env-file`: https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/
