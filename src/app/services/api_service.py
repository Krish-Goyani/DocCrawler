import httpx

from src.app.core.error_handler import JsonResponseError


class ApiService:
    def __init__(self) -> None:
        self.timeout = httpx.Timeout(
            connect=60.0,  # Time to establish a connection
            read=150.0,  # Time to read the response
            write=150.0,  # Time to send data
            pool=60.0,  # Time to wait for a connection from the pool
        )

    async def get(
        self, url: str, headers: dict = None, data: dict = None
    ) -> httpx.Response:
        """
        Sends an asynchronous GET request with a timeout.
        :param url: The URL to send the request to.
        :param headers: Optional HTTP headers.
        :param data: Optional query parameters.
        :return: The HTTP response.
        """
        try:

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, params=data)
                response.raise_for_status()
                try:
                    return response.json()
                except:
                    return response.text
        except httpx.RequestError as exc:
            error_msg = (
                f"An error occurred while requesting {exc.request.url!r}."
            )
            raise JsonResponseError(status_code=500, detail=error_msg)
        except httpx.HTTPStatusError as exc:
            error_msg = f"Error response {exc.response.status_code} while requesting {exc.request.url!r}. \n error from api_service in get()"
            raise JsonResponseError(
                status_code=exc.response.status_code, detail=error_msg
            )

    async def post(
        self,
        url: str,
        headers: dict = None,
        data: dict = None,
        files: dict = None,
    ) -> httpx.Response:
        """
        Sends an asynchronous POST request with a timeout.
        :param url: The URL to send the request to.
        :param headers: Optional HTTP headers.
        :param data: The payload to send in JSON format.
        :return: The HTTP response.
        """
        try:
            timeout = httpx.Timeout(90.0)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if files:
                    response = await client.post(
                        url, headers=headers, data=data, files=files
                    )
                else:
                    response = await client.post(
                        url, headers=headers, json=data
                    )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            raise JsonResponseError(
                status_code=500,
                detail=f"API request failed with error: {str(exc)} \n error from api_service in post()",
            )
        except httpx.HTTPStatusError as exc:
            raise JsonResponseError(
                status_code=500,
                detail=f"API request failed with error: {str(exc)} \n error from api_service in post()",
            )
        except Exception as exc:
            raise JsonResponseError(
                status_code=500,
                detail=f"API request failed with error: {str(exc)} \n error from api_service in post()",
            )
