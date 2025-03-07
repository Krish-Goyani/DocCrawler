from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.app.config.database import mongodb_database
from src.app.routes.scraper_route import scrape_router


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    mongodb_database.connect()

    yield

    mongodb_database.disconnect()


app = FastAPI(lifespan=db_lifespan)
app.include_router(router= scrape_router)
