from pathlib import Path

from fastapi import FastAPI
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import (
    routes_chat,
    routes_documents,
    routes_health,
    routes_knowledge,
    routes_opportunities,
    routes_pilots,
    routes_process_scanner,
    routes_tools,
)
from app.api.labs import router as labs_router
from app.config import get_settings
from app.core.db import init_db
from app.deps import require_admin_access

STATIC_DIR = Path(__file__).resolve().parent / "static"
settings = get_settings()

app = FastAPI(
    title="VirtuDirector IA",
    version="0.4.0",
    description="CAIO fraccional aumentado por IA with FDE Labs.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:8000"]
    if settings.environment != "production"
    else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "service": "virtudirector-ia",
        "demo_mode": settings.demo_mode,
    }


app.include_router(routes_health.router)
app.include_router(routes_chat.router)
app.include_router(routes_documents.router)
app.include_router(routes_knowledge.router)
app.include_router(routes_opportunities.router)
app.include_router(routes_pilots.router)
app.include_router(routes_process_scanner.router)
app.include_router(routes_tools.router)
app.include_router(labs_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/admin/labs", include_in_schema=False)
def labs_admin(_admin=Depends(require_admin_access)) -> FileResponse:
    return FileResponse(STATIC_DIR / "admin-labs.html")


@app.get("/app", include_in_schema=False)
def caio_app() -> FileResponse:
    return FileResponse(STATIC_DIR / "caio-chat.html")


@app.get("/")
async def root() -> dict:
    return {
        "service": "VirtuDirector IA",
        "docs": "/docs",
        "app": "/app",
        "admin_labs": "/admin/labs",
        "demo_mode": settings.demo_mode,
    }
