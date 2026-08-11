from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Green Brain Tourism",
    description="Туристический сайт-приветствие"
)

os.makedirs(BASE_DIR / "static" / "images", exist_ok=True)
os.makedirs(BASE_DIR / "static" / "css", exist_ok=True)
os.makedirs(BASE_DIR / "static" / "js", exist_ok=True)
os.makedirs(BASE_DIR / "templates", exist_ok=True)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    destinations = [
        {
            "name": "Мальдивы",
            "description": "Райские острова с кристально чистой водой",
            "image": "🏝️"
        },
        {
            "name": "Швейцария",
            "description": "Величественные Альпы и озера",
            "image": "🏔️"
        },
        {
            "name": "Япония",
            "description": "Уникальная культура и традиции",
            "image": "⛩️"
        },
        {
            "name": "Италия",
            "description": "Искусство, история и кулинария",
            "image": "🍕"
        },
        {
            "name": "Исландия",
            "description": "Северное сияние и гейзеры",
            "image": "🌌"
        },
        {
            "name": "Бали",
            "description": "Тропический рай для отдыха",
            "image": "🌴"
        }
    ]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "destinations": destinations
    })


@app.get("/api/destinations")
async def get_destinations():
    return {
        "destinations": [
            {"name": "Мальдивы", "country": "Мальдивы", "price": "1500$"},
            {"name": "Париж", "country": "Франция", "price": "800$"},
            {"name": "Токио", "country": "Япония", "price": "1200$"},
            {"name": "Нью-Йорк", "country": "США", "price": "1000$"}
        ]
    }


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    