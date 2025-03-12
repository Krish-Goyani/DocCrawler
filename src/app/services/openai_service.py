from fastapi import Depends
import json
from src.app.config.settings import settings
from src.app.core.error_handler import JsonResponseError
from src.app.services.api_service import ApiService

import aiofiles

class OpenAIService:
    def __init__(self, api_service: ApiService = Depends()) -> None:
        self.api_service = api_service
        self.base_url = settings.OPENAI_BASE_URL
        self.completion_endpoint = settings.OPENAI_COMPLETION_ENDPOINT
        self.file_endpoint = settings.OPENAI_FILE_ENDPOINT
        self.openai_model = settings.OPENAI_MODEL
        self.batch_endpoint = settings.OPENAI_BATCH_ENDPOINT

    async def completions(self, prompt: str, **params) -> dict:
        """
        This method is responsible for sending a POST request to the OpenAI API
        to get completions for the given prompt.
        :param prompt: The prompt to get completions for.
        :param params: The optional parameters.
        :return: The completions for the given prompt.
        """
        url = f"{self.base_url}{self.completion_endpoint}"

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
            raise JsonResponseError(status_code=500, detail=str(e))

    async def upload_jsonl_file(self, jsonl_file, purpose):
        url = f"{self.base_url}{self.file_endpoint}"
        
        headers = {"Authorization": f"Bearer {settings.OPENAI_KEY}"}
        payload = {"purpose": purpose}
        
        async with aiofiles.open(jsonl_file, "rb") as f:
            file_content = await f.read()
            
        # Prepare multipart file format
        files = {"file": (jsonl_file, file_content, "application/json")}
        
        try:
            response = await self.api_service.post(url, headers=headers, data=payload, files=files)
            print(response)
            return response.get("id")
        except Exception as e:
            raise JsonResponseError(status_code=500, detail=str(e))
            
            
    async def create_batch_request(self, file_id):
        
        url = f"{self.base_url}{self.batch_endpoint}"
        
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "input_file_id": file_id,
            "endpoint": "/v1/chat/completions",
            "completion_window": "24h"
        }
        
        try:
            response = await self.api_service.post(url, headers=headers, data=payload)
            print(response)
            return response.get("id")
        except Exception as e:
            raise JsonResponseError(status_code=500, detail=str(e))
        
    async def get_batch_status(self, batch_id):

        url = f"{self.base_url}{self.batch_endpoint}/{batch_id}"
        
        headers = {"Authorization": f"Bearer {settings.OPENAI_KEY}"}
        
        try:
            response = await self.api_service.get(url, headers=headers)
            return response
        except Exception as e:
            raise JsonResponseError(status_code=500, detail=e)
        
        
    async def retrieve_file_content(self, file_id):
        
        url = f"{self.base_url}{self.file_endpoint}/{file_id}/content"
        print(url)
        
        headers = {"Authorization": f"Bearer {settings.OPENAI_KEY}"}
        
        try:
            response = await self.api_service.get(url, headers=headers)
            return response
        except Exception as e:
            raise JsonResponseError(status_code=500, detail=e)