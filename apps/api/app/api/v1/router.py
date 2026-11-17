"""Router de la API pública v1 (requiere JWT de Supabase salvo que se indique lo contrario)."""

from fastapi import APIRouter

from app.api.v1 import athlete, calendar, integrations, me

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(me.router)
api_v1_router.include_router(integrations.router)
api_v1_router.include_router(athlete.router)
api_v1_router.include_router(calendar.router)
