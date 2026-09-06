"""Custom exception handler for Risk-Guard API."""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Wrap DRF's default handler to ensure consistent error format:
    { "detail": "...", "code": "..." }
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Ensure 'code' is present
        if isinstance(response.data, dict) and "code" not in response.data:
            response.data["code"] = _status_to_code(response.status_code)
        return response

    # Unhandled exceptions → 500
    return Response(
        {"detail": "An unexpected error occurred.", "code": "server_error"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _status_to_code(status_code: int) -> str:
    """Map HTTP status codes to short error code strings."""
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        429: "throttled",
    }
    return mapping.get(status_code, "error")
