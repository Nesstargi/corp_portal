# Docker Deploy For `testcorpportal.xyz`

## What You Need

- A VPS or any server where Docker and Docker Compose are available
- Ports `80` and `443` open on the server
- DNS access for `testcorpportal.xyz`

## DNS

Point your domain to the server IP:

- `A` record for `testcorpportal.xyz` -> your server IPv4
- Optional: `A` record for `www.testcorpportal.xyz` -> the same IPv4

If you use Cloudflare, start with `DNS only` while issuing the first certificate.

## Server Setup

Copy the project to the server and create the production env file:

```bash
cp .env.production.example .env.production
```

Then fill in:

- `DOMAIN=testcorpportal.xyz`
- `POSTGRES_PASSWORD=...`
- `SECRET_KEY=...`
- `ALLOWED_HOSTS=testcorpportal.xyz`
- `CSRF_TRUSTED_ORIGINS=https://testcorpportal.xyz`

## Start The Project

```bash
docker compose up -d --build
```

Then check:

```bash
docker compose ps
docker compose logs -f caddy
docker compose logs -f web
```

## Create Admin User

```bash
docker compose exec web python manage.py createsuperuser
```

## If You Need Current Local Data

Export locally:

```bash
python manage.py dumpdata --exclude auth.permission --exclude contenttypes > data.json
```

Copy `data.json` to the server, then import:

```bash
docker compose exec web python manage.py loaddata data.json
```

## Useful Commands

Restart:

```bash
docker compose restart
```

Rebuild after code changes:

```bash
docker compose up -d --build
```

Open Django shell:

```bash
docker compose exec web python manage.py shell
```

## Notes

- Caddy issues and renews HTTPS certificates automatically.
- PostgreSQL data is stored in the `postgres_data` volume.
- Uploaded files are stored in the `media_data` volume.
