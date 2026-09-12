from django.db import connection
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception: # noqa: BLE001 - health check must report any DB failure as unavailable
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
