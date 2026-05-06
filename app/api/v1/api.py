from fastapi import APIRouter
from app.api.v1.routes import health
from app.api.v1.routes import claims

api_router = APIRouter()

api_router.include_router(health.api_router, prefix="/v1")
api_router.include_router(claims.api_router, prefix="/v1")



