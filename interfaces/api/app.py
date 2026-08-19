"""
interfaces/api/app.py — FastAPI приложение (заглушка для v2.0).
Version: 0.1.0 (TODO)
Description: REST API для веб-интерфейса и внешних клиентов.
"""
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# 
# app = FastAPI(
#     title="Tutu Travel Agent API",
#     version="2.0.0",
#     description="REST API для мультиагентной системы туроператора",
# )
# 
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# 
# @app.get("/health")
# async def health_check():
#     return {"status": "ok", "version": "2.0.0"}
# 
# @app.post("/chat")
# async def chat_endpoint(message: str):
#     # TODO: Интеграция с Orchestrator
#     return {"response": "API в разработке", "message": message}
# 
# @app.get("/tools")
# async def list_tools():
#     # TODO: Возврат списка доступных инструментов
#     return {"tools": []}

print("🚧 API модуль в разработке (v2.0)")
print("   Для запуска используйте: python main.py --mode cli")