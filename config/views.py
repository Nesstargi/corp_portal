from django.http import HttpResponse


def healthcheck(request):
    return HttpResponse("ok", content_type="text/plain")
