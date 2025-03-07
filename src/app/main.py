from src.app.routes.scraper_route import router
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.app.config.database import mongodb_database


@asynccontextmanager
async def db_lifespan(app: FastAPI):
    mongodb_database.connect()

    yield
    
    mongodb_database.disconnect()
    
app = FastAPI(lifespan= db_lifespan)
app.include_router(router)


