from fastapi import Depends

from src.app.config.settings import settings
from src.app.core.error_handler import JsonResponseError
from src.app.services.api_service import ApiService


class OpenAIService:
    def __init__(self, api_service: ApiService = Depends()) -> None:
        self.api_service = api_service
        self.base_url = settings.OPENAI_URL
        # self.endpoint = "chat/completions"
        self.openai_model = settings.OPENAI_MODEL

    async def completions(self, prompt: str, **params) -> dict:
        """
        This method is responsible for sending a POST request to the OpenAI API
        to get completions for the given prompt.
        :param prompt: The prompt to get completions for.
        :param params: The optional parameters.
        :return: The completions for the given prompt.
        """
        url = f"{self.base_url}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_KEY}",
        }

        payload = {
            "model": self.openai_model,
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
            return response
        except Exception as e:
            raise JsonResponseError(
                status_code=500,
                detail=f"Error while sending a POST request to the OpenAI API: {str(e)} \n error from openai_service in completions()",
            )
