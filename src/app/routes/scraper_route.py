from typing import Annotated, List

from fastapi import APIRouter, Depends

from src.app.controllers.scrape_controller import ScrapeController

scrape_router = APIRouter()


@scrape_router.post("/")
async def scrape_docs(
    urls: List[str], scrape_controller: Annotated[ScrapeController, Depends()]
):
    try:
        # response = await scrape_controller.scrape(str(uuid.uuid4()), urls)
        response = await scrape_controller.process_embeddings(user_id="123")
        # return response
        return {
            "user_id": response,
            "message": "Embeddings processed successfully",
        }
    except Exception as e:
        print(e)
        return {"error": str(e)}
