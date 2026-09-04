from fastapi import APIRouter

from app.api.v1 import (air_quality, alerts, analytics, auth, command_center,
                         copilot, health, predictions, recommendations,
                         simulation, sources, system)

api_router = APIRouter(prefix="/api/v1")

for module in (system, auth, air_quality, predictions, sources, analytics,
               simulation, recommendations, alerts, health, copilot,
               command_center):
    api_router.include_router(module.router)
