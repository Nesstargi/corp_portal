import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .services import TelegramBotError, handle_update, telegram_enabled


@csrf_exempt
def webhook(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    if not telegram_enabled():
        return HttpResponse("Telegram disabled", status=503)

    if settings.TELEGRAM_WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret_header != settings.TELEGRAM_WEBHOOK_SECRET:
            return HttpResponseForbidden("Invalid webhook secret")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "invalid-json"}, status=400)

    try:
        handle_update(payload)
    except TelegramBotError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

    return JsonResponse({"ok": True})

