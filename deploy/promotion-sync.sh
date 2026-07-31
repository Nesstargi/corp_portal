#!/bin/sh

interval="${PROMOTION_SYNC_INTERVAL_SECONDS:-3600}"

case "$interval" in
  ''|*[!0-9]*) interval=3600 ;;
esac

if [ "$interval" -lt 60 ]; then
  interval=60
fi

echo "Promotion sync started; interval: ${interval}s"

while true; do
  echo "[$(date '+%Y-%m-%dT%H:%M:%S%z')] Synchronizing promotion sources"
  python manage.py sync_promotion_sources || true
  sleep "$interval"
done
