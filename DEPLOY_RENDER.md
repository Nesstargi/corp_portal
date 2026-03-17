# Deploy To Render

## What This Setup Expects

- A Git repository with this project
- A Render web service
- A Render PostgreSQL database
- A persistent disk mounted to `/opt/render/project/src/media` if you want uploaded images and files to survive redeploys

## Render Web Service Settings

- Environment: `Python`
- Build Command: `bash build.sh`
- Start Command: `gunicorn config.wsgi:application`
- Health Check Path: `/health/`

## Environment Variables

- `SECRET_KEY`: long random string
- `DEBUG`: `False`
- `ALLOWED_HOSTS`: your Render hostname and custom hostname, comma-separated
- `CSRF_TRUSTED_ORIGINS`: full `https://...` origins, comma-separated
- `DATABASE_URL`: from Render PostgreSQL
- `SECURE_SSL_REDIRECT`: `True`
- `SECURE_HSTS_SECONDS`: `3600`
- `SERVE_MEDIA`: `True`

## Custom Domain

1. Add the custom domain in Render.
2. Copy the DNS records Render gives you.
3. Add those records at your domain registrar or in Cloudflare DNS.
4. After the domain is verified, add the same host to `ALLOWED_HOSTS` and the `https://...` origin to `CSRF_TRUSTED_ORIGINS`.

## First Login

After deploy, create an admin user from the Render shell:

```bash
python manage.py createsuperuser
```
