from fastapi import Depends

from src.app.config.settings import settings
from src.app.services.api_service import ApiService
from src.app.utils.error_handler import JsonResponseError


class OpenAIService:
    def __init__(self, api_service=Depends(ApiService)) -> None:
        self.api_service = api_service

    async def get_completion(self, prompt: str, **params) -> dict:
        url = settings.OPENAI_URL  # Ensure this is set to
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_KEY}",
        }
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {
                    "role": "developer",
                    "content": "You are a helpful assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            **params,
        }
        try:
            response = await self.api_service.post(
                url, headers=headers, data=payload
            )
        except Exception as e:
            raise JsonResponseError(status_code=500, detail=str(e))
        return response
