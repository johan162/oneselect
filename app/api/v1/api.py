from fastapi import APIRouter

from app.api.v1.endpoints import (
    login,
    auth,
    users,
    projects,
    features,
    comparisons,
    statistics,
    results,
    model_config,
    admin,
)

api_router = APIRouter()
api_router.include_router(login.router, prefix="/auth", tags=["auth"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
# Features and comparisons are nested under projects
api_router.include_router(features.router, prefix="/projects", tags=["features"])
api_router.include_router(comparisons.router, prefix="/projects", tags=["comparisons"])
# Statistics, results, and model config are nested under projects
api_router.include_router(statistics.router, prefix="/projects", tags=["statistics"])
api_router.include_router(results.router, prefix="/projects", tags=["results"])
api_router.include_router(model_config.router, prefix="/projects", tags=["model"])
# Admin endpoints
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
