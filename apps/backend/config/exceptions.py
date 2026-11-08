"""Stable error envelope for the native client (DC-103).

Field-level validation errors keep their field keys; when the response is a
dictionary without a ``code`` key we add a stable top-level code. Existing
endpoints that already return a ``code`` (for example ``insufficient_balance``)
are left untouched.
"""
from rest_framework.views import exception_handler

STATUS_CODES = {
    400: "validation_error",
    401: "authentication_failed",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    410: "gone",
    413: "payload_too_large",
    415: "unsupported_media_type",
    429: "too_many_requests",
    500: "server_error",
}


def spendy_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    if isinstance(data, dict) and "code" not in data:
        data["code"] = STATUS_CODES.get(response.status_code, "error")
    return response
