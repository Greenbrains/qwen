"""
FastAPI приложение.
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from .routes import router as api_router
from .websocket import router as ws_router
from interfaces.dependencies import app_dependencies

logger = logging.getLogger("travel_agent.api")

# ❗ Было Path(file)
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

@app.get("/")
async def index():
    """Веб-интерфейс агента."""
    index_file = WEB_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(
            f"<h1>index.html не найден</h1><p>Ищу здесь: {index_file}</p>",
            status_code=404
        )
    return FileResponse(index_file)
