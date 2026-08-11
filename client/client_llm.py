"""
Фабрика LLM-клиентов. Клиент не зависит от модели (модель — параметр
запроса), поэтому кэшируется по credentials: все агенты с одним ключом singletone 
делят один клиент.
"""

from threading import Lock
from openai import OpenAI
from config import get_settings

class LLMClient:
    _lock = Lock()
    _clients: dict[tuple[str, str, str | None], OpenAI] = {}

    @classmethod
    def get_client(
        cls,
        settings=None,
        api_key:  str | None = None,
        base_url: str | None = None,
        project:  str | None = None,
    ) -> OpenAI:
        
        settings = settings or get_settings()
        key = (
            base_url or settings.yandex_base_url,
            api_key or settings.api_key,
            project or settings.yandex_folder_id,
        )
        with cls._lock:
            if key not in cls._clients:
                cls._clients[key] = OpenAI(
                    api_key=key[1], base_url=key[0], project=key[2]
                )
            return cls._clients[key]

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._clients.clear()

