import traceback
from functools import wraps

from fastapi.responses import JSONResponse


class JsonResponseError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.detail = detail
        self.response = JSONResponse(
            status_code=status_code, content={"detail": detail}
        )


def error_handler(func):
    """
    Decorator to catch JsonResponseError or any other exceptions raised
    from deeper layers and return a JSONResponse with traceback details.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except JsonResponseError as json_exc:
            trace = traceback.format_exc()
            return JSONResponse(
                status_code=json_exc.response.status_code,
                content={
                    "detail": json_exc.detail,
                    "traceback": trace.split("\n"),
                },
            )
        except Exception as exc:
            # Capture full traceback details
            trace = traceback.format_exc()

            # Return the error message along with the full call stack
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal Server Error",
                    "error": str(exc),
                    "traceback": trace.split(
                        "\n"
                    ),  # Split into list for better readability
                },
            )

    return wrapper
