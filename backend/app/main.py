from fastapi import FastAPI

from app.api.health import router as health_router
from app.config.settings import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)
app.include_router(health_router)
