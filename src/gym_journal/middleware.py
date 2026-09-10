import logging
import time
import uuid

logger = logging.getLogger("gym_journal")

SKIP_PATH_PREFIXES = ("/health/", "/static/")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = str(uuid.uuid4())
        request.request_id = request_id

        if request.path.startswith(SKIP_PATH_PREFIXES):
            response = self.get_response(request)
            response["X-Request-ID"] = request_id
            return response

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - start) * 1000)

        user = getattr(request, "user", None)
        user_id = user.pk if user is not None and user.is_authenticated else None

        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        client_ip = forwarded_for.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "")

        logger.info(
            "request completed",
            extra={
                "event": "request.completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
                "client_ip": client_ip,
            },
        )
        response["X-Request-ID"] = request_id
        return response
