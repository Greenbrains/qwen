"""
Локальный запуск FastAPI-сервера (REST + WebSocket + веб-UI).
"""
import uvicorn
from config import get_settings

def main() -> None:
    settings = get_settings()
    print(f"🚀 Tutu Travel Agent API: http://localhost:{settings.api_port}")
    print("   Веб-чат:  GET  /")
    print("   REST:     POST /chat, GET /health, GET /tools")
    print("   WS:       /ws (текст), /ws/voice (голос)")
    uvicorn.run(
        "interfaces.api.app:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=False,
    )

if __name__ == "__main__":
    main()
