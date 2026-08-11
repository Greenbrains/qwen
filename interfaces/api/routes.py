"""REST эндпоинты."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from interfaces.dependencies import get_dependencies

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_name: str
    tool_calls: List[Dict[str, Any]] = []

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    deps = get_dependencies()
    session = deps.session_store.get_or_create(request.session_id)
    last_agent = getattr(session, "last_agent", None)

    final_text, messages, tool_calls, agent_name = await deps.orchestrator.run(request.message, session.history, last_agent)
    
    session.messages = messages
    session.last_agent = agent_name
    session.record_tool_calls(tool_calls)
    deps.session_store.save(session)

    return ChatResponse(response=final_text, session_id=session.session_id, agent_name=agent_name, tool_calls=tool_calls)

@router.get("/health")
async def health(): return {"status": "ok"}
