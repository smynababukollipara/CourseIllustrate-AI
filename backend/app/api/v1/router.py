from fastapi import APIRouter
from app.api.v1.documents import router as documents_router
from app.api.v1.generations import router as generations_router

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(documents_router)
api_v1_router.include_router(generations_router)
