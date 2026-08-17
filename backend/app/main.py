from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="ModelCouncil API",
    version="0.1.0",
    description="Web API for synthetic consumer simulation and opinion dynamics.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "ModelCouncil API",
        "status": "initialized",
        "docs": "/docs",
    }
