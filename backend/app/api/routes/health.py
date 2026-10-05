"""Health check routes."""
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    llm_provider: str


@router.get("/health", response_model=HealthResponse, summary="Health Check")
async def health_check():
    """Returns service health status."""
    return HealthResponse(
        status="healthy",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        llm_provider=settings.llm_provider,
    )
