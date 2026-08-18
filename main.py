# main.py
# Version: main_v4.0
# Description: Orchestrator for Multi-Agent System with Skills Catalog (YandexGPT backend)
# Features: Skills loading, Token logging, Dynamic context, YandexGPT integration

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

# Загрузка переменных окружения
load_dotenv()

# --- КОНФИГУРАЦИЯ ---
API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")


# --- ЛОГГИРОВАНИЕ ---
LOG_FILE = os.getenv("LOG_FILE", "logs.txt")

# Настройка логгера: только в файл, без консоли
logger = logging.getLogger("TutuAgent_v4")
logger.setLevel(logging.INFO)

# Очистка старых хендлеров
if logger.hasHandlers():
    logger.handlers.clear()

file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- МОДЕЛИ ---
MODEL_ROUTER = os.getenv("YANDEX_MODEL_ROUTER", "yandexgpt-lite")
MODEL_AGENT = os.getenv("YANDEX_MODEL_AGENT", "yandexgpt")

class YandexGPTClient:
    """Клиент для работы с YandexGPT через OpenAI-совместимый API"""
    def __init__(self, api_key: str, folder_id: str):
        self.folder_id = folder_id
        # Используем официальный OpenAI-совместимый эндпоинт Яндекса
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://ai.api.cloud.yandex.net/v1",
            project=folder_id,
        )

    def generate(self, messages: List[Dict], model: str = "yandexgpt-lite", temperature: float = 0.7, max_tokens: int = 2000) -> tuple[str, int, int]:
        """
        Генерация ответа. Возвращает (text, input_tokens, output_tokens)
        """
        model_uri = f"gpt://{self.folder_id}/{model}"
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=model_uri,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            result_text = response.choices[0].message.content or ""
            
            # Получение токенов (если API их вернул)
            input_tokens = getattr(response.usage, 'prompt_tokens', 0) if response.usage else 0
            output_tokens = getattr(response.usage, 'completion_tokens', 0) if response.usage else 0
            
            duration = time.time() - start_time
            logger.info(f"Model: {model} | In: {input_tokens} | Out: {output_tokens} | Time: {duration:.2f}s")
            
            return result_text, input_tokens, output_tokens
            
        except Exception as e:
            logger.error(f"Error calling YandexGPT: {str(e)}")
            raise

class SkillsCatalog:
    """Управление каталогом навыков (Skills Catalog)"""
    
    def __init__(self):
        self.skills_dir = "skills"
        self.loaded_skill: Optional[Dict] = None
        self.catalog_path = os.path.join(self.skills_dir, "catalog.md")
        
    def load_catalog(self) -> str:
        """Читает файл каталога и возвращает его содержимое для промпта"""
        if not os.path.exists(self.catalog_path):
            return "Каталог навыков не найден."
        
        with open(self.catalog_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    def load_skill(self, skill_name: str) -> Optional[Dict]:
        """Загружает конкретный навык по имени"""
        skill_file = os.path.join(self.skills_dir, f"{skill_name}.md")
        if not os.path.exists(skill_file):
            logger.warning(f"Skill '{skill_name}' not found.")
            return None
            
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Парсинг простого формата: имя, описание, инструкция
        # В реальной системе можно использовать более сложный парсер
        self.loaded_skill = {
            "name": skill_name,
            "content": content
        }
        logger.info(f"Loaded skill: {skill_name}")
        return self.loaded_skill

class AgentOrchestrator:
    """Основной оркестратор системы"""
    
    def __init__(self):
        if not API_KEY or not FOLDER_ID:
            raise ValueError("Отсутствуют YANDEX_API_KEY или YANDEX_FOLDER_ID в .env")
            
        self.client = YandexGPTClient(API_KEY, FOLDER_ID)
        self.skills = SkillsCatalog()
        self.history: List[Dict] = []
        self.current_skill_context = ""
        
        # Системный промпт роутера
        self.router_system_prompt = """
Ты - Роутер (Router) в мультиагентной системе.
Твоя задача: определить намерение пользователя и выбрать подходящий навык (Skill) из Каталога.
Если пользователь хочет подобрать путешествие (билеты, отели, туры) -> выбери 'touragent'.
Если пользователь хочет маркетинговый анализ, копирайтинг, SEO -> выбери 'marketingskills'.
Если запрос не подходит ни под один навык -> верни 'general'.

Ответ должен быть ТОЛЬКО именем навыка (например: touragent), без лишних слов.
"""
        # Базовый системный промпт агента (заполняется динамически)
        self.agent_base_prompt = """
Ты - специализированный ИИ-ассистент.
Твоя задача: выполнить запрос пользователя, строго следуя инструкциям загруженного навыка.
Используй инструменты только так, как описано в навыке.
Экономь токены: не запрашивай лишние данные, используй компактные ответы.
"""

    def route_request(self, user_message: str) -> str:
        """Определяет нужный навык"""
        catalog_content = self.skills.load_catalog()
        messages = [
            {"role": "system", "content": f"{self.router_system_prompt}\n\nДоступные навыки:\n{catalog_content}"},
            {"role": "user", "content": user_message}
        ]
        
        response, _, _ = self.client.generate(messages, model=MODEL_ROUTER, temperature=0.0)
        return response.strip().lower()

    def process_with_skill(self, skill_name: str, user_message: str):
        """Обрабатывает запрос с использованием конкретного навыка"""
        skill_data = self.skills.load_skill(skill_name)
        if not skill_data:
            return "Ошибка: Навык не найден. Попробуйте другой запрос."
        
        # Формируем контекст навыка
        system_instruction = f"{self.agent_base_prompt}\n\nИНСТРУКЦИЯ НАВЫКА ({skill_name}):\n{skill_data['content']}"
        
        # Добавляем историю (с ограничением keep_last_turns)
        # Для простоты берем последние 5 сообщений + текущее
        context_messages = self.history[-10:] if len(self.history) > 10 else self.history
        
        messages = [
            {"role": "system", "content": system_instruction},
            *context_messages,
            {"role": "user", "content": user_message}
        ]
        
        response, in_tok, out_tok = self.client.generate(messages, model=MODEL_AGENT, temperature=0.7)
        
        # Обновляем историю
        self.history.append({"role": "user", "content": user_message})
        self.history.append({"role": "assistant", "content": response})
        
        return response

    def chat_loop(self):
        """Основной цикл чата"""
        print("="*60)
        print("🧳 Tutu Travel Agent v4.0 — Консольный режим (YandexGPT)")
        print("="*60)
        print("Команды: /help, /clear, /log, /exit")
        print("="*60)
        
        logger.info("Session started")
        
        while True:
            try:
                user_input = input("\n👤 Вы: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == "/exit":
                    logger.info("Session ended by user")
                    break
                elif user_input.lower() == "/help":
                    print("Доступные команды: /help, /clear, /log, /exit")
                    print("Просто напишите запрос, например: 'Подбери тур в Сочи'")
                    continue
                elif user_input.lower() == "/clear":
                    self.history = []
                    print("🗑️ История очищена.")
                    logger.info("History cleared")
                    continue
                elif user_input.lower() == "/log":
                    abs_path = os.path.abspath(LOG_FILE)
                    print(f"📄 Логи сохраняются в: {abs_path}")
                    continue
                
                # Логирование входа
                logger.info(f"User input: {user_input[:50]}...")
                
                # 1. Роутинг
                print("🤖 Анализ запроса...")
                skill_name = self.route_request(user_input)
                logger.info(f"Routed to skill: {skill_name}")
                
                # 2. Выполнение
                print(f"🤖 Активация навыка: {skill_name}...")
                response = self.process_with_skill(skill_name, user_input)
                
                print(f"🤖 Агент: {response}")
                
            except KeyboardInterrupt:
                print("\n👋 Принудительный выход.")
                break
            except Exception as e:
                error_msg = str(e)
                print(f"🤖 Агент: Произошла ошибка: {error_msg}")
                logger.error(f"Critical error: {error_msg}")

if __name__ == "__main__":
    try:
        app = AgentOrchestrator()
        app.chat_loop()
    except ValueError as ve:
        print(f"❌ Ошибка конфигурации: {ve}")
        print("Проверьте файл .env и наличие ключей YANDEX_API_KEY и YANDEX_FOLDER_ID")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка запуска: {e}")
        sys.exit(1)

