"""
FastAPI приложение.
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from config import get_all_destinations


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from .routes import router as api_router
from .websocket import router as ws_router
from interfaces.dependencies import app_dependencies

logger = logging.getLogger("travel_agent.api")

#  Path(file)
WEB_DIR = Path(__file__).resolve().parent.parent / "web"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Инициализация зависимостей...")
    await app_dependencies.startup()
    print("🚀 Сервер запущен")
    
    yield
    
    # Shutdown
    print("🛑 Остановка сервера...")
    await app_dependencies.shutdown()
    print("🛑 Сервер остановлен")

app = FastAPI(
    title="Tutu Travel Agent API",
    description="REST/WebSocket API для туристического агента",
    version="2.1.0",
    lifespan=lifespan,
)

# ❗ Добавлены решётки, иначе SyntaxError
# CORS — чтобы локальный веб-UI и внешние фронты могли ходить в API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(ws_router)

# ================= Green Brain web UI =================

@app.get("/", response_class=HTMLResponse)
async def gb_landing():
    return FileResponse(WEB_DIR / "index.html")

@app.get("/chat.html", response_class=HTMLResponse)
async def gb_chat():
    return FileResponse(WEB_DIR / "chat.html")

@app.get("/api/destinations")
async def gb_destinations():
    return {"destinations": [
        {"destination_id": d.destination_id, "name": d.name,
         "emoji": d.emoji, "description": d.description}
        for d in get_all_destinations()
    ]}

@app.get("/api/destinations/{dest_id}")
async def gb_destination(dest_id: str):
    for d in get_all_destinations():
        if d.destination_id == dest_id:
            return {"destination_id": d.destination_id, "name": d.name,
                    "emoji": d.emoji, "description": d.description,
                    "full_description": getattr(d, "full_description", d.description)}
    return JSONResponse({"error": "destination not found"}, status_code=404)

app.mount("/static", StaticFiles(directory=str(WEB_DIR / "static")), name="static")
# ======================================================
