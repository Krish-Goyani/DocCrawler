import uuid

from fastapi import APIRouter, Depends

from src.app.controllers.scrape_controller import ScrapeController
from src.app.utils.error_handler import error_handler
from typing import List

router = APIRouter()


@error_handler
@router.post("/scrape")
async def scrape(urls: List, scrape_controller=Depends(ScrapeController)):
    return await scrape_controller.scrape(str(uuid.uuid4()), urls)
