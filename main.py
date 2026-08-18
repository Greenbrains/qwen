import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel

# Модель данных для чата
class ChatRequest(BaseModel):
    message: str
    history: list = []
    context: dict = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Green Brain Travel Agent Starting...")
    # Здесь можно инициализировать клиента агента
    yield
    print("🛑 Service Stopping...")

app = FastAPI(title="Green Brain Travel Agent", lifespan=lifespan)

# Настройка путей к статике и шаблонам
# Ищем папку interfaces/web или просто web в корне проекта
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "interfaces" / "web"
if not WEB_DIR.exists():
    WEB_DIR = BASE_DIR / "web"
if not WEB_DIR.exists():
    WEB_DIR = BASE_DIR # Фоллбэк на корень

STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

# Подключаем статику если есть папка
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Настраиваем шаблоны
templates = Jinja2Templates(directory=str(TEMPLATES_DIR) if TEMPLATES_DIR.exists() else str(WEB_DIR))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/agent", response_class=HTMLResponse)
async def agent_page(request: Request):
    """Страница выбора направлений и чата"""
    return templates.TemplateResponse("agent.html", {
        "request": request, 
        "title": "Travel Agent - Green Brain"
    })

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Эндпоинт для общения с агентом"""
    # ЗАГЛУШКА: Здесь нужно вызвать реальную логику вашего агента
    # Например: response = await agent.process(req.message, req.context)
    
    country = req.context.get("country", "миром")
    user_msg = req.message
    
    # Имитация ответа агента
    response_text = f"Отличный выбор! Для направления '{country}' я могу подобрать туры. Вы спросили: '{user_msg}'. Сейчас анализирую предложения..."
    
    return {
        "response": response_text,
        "status": "success",
        "context": {"country": country}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
