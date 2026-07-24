from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.config.settings import get_settings
from app.domain.contracts import RuntimeMode


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    app_name: str
    status: str
    mode: RuntimeMode


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        app_name=settings.app_name,
        status="ok",
        mode=settings.mode,
    )
