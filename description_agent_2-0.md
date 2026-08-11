# Архитектура Tutu Travel Agent (актуальное состояние)

Модульная архитектура: один и тот же агент работает в трёх сценариях —
консоль (синхронный), FastAPI REST/WebSocket (асинхронный), голосовой Realtime WebSocket.

## Зоны ответственности
config/ — .env + Settings (pydantic): ключи Yandex, MCP URL, лимиты, логи
agent/core/ — инфраструктура: MCP-клиенты, промпты, реестр инструментов, скилы
agent/ — ядро агента: базовый цикл, реализации, сессия, обработчики WS
interfaces/ — точки входа: cli.py, dependencies.py, api/ (FastAPI)
main.py — выбор режима (--mode console|api|websocket)


## Ядро агента (agent/)
- **base.py — BaseAgent.** Владеет всем агентным циклом (sync и async):
  построение сообщений, парсинг tool calls (включая обёртку `tutu_mcp`
  `{"tool_name", "arguments"}`), форматирование MCP-результатов (`mcp_result_to_text`
  с подсказками для пустых offers/variants), retry при пустом финале, лимит итераций.
  Подкласс реализует только `_chat_sync/_chat_async` и `_execute_tool_sync/_execute_tool_async`.
- **openai_agent.py** — `OpenAIAgent` (openai.OpenAI + SyncMCPClient) и
  `AsyncOpenAIAgent` (openai.AsyncOpenAI + AsyncMCPClient): тонкие подклассы, весь цикл унаследован от BaseAgent.
- **realtime_agent.py** — голосовой режим: WebSocket к Yandex Realtime API,
  `session.update` с инструкциями (промпт с датой), проксирование аудио (PCM base64), обработка `function_call` через handlers.py.
- **handlers.py** — `handle_function_call`: выполняет MCP-инструмент и возвращает `function_call_output` + `response.create`.
- **session.py** — `Session` (история, tool-calls) и `SessionStore` (in-memory, TTL) для API.

## Инфраструктура (agent/core/)
- **mcp/**: `SyncMCPClient` (requests) / `AsyncMCPClient` (aiohttp) — JSON-RPC 2.0,
  рукопожатие initialize → notifications/initialized → tools/list; заголовки
  `Accept: application/json, text/event-stream` + `MCP-Protocol-Version`;
  парсинг JSON и SSE; сохранение `Mcp-Session-Id`; таймаут 120 c на вызов.
  `checkout_helper.py` — сборка arguments для `create_checkout_link`
  (распаковка `checkout_ref`). `models.py` — Pydantic JSON-RPC.
- **prompts/**: единственный источник промптов. 
  `PromptLoader` рендерит 
  `system_prompt.jinja` (блок текущей даты вычисляется при каждом рендере)
  с include `travel_assistant.md` + `mcp_instructions.md` + `mcp_tools_rules.md`
  и JSON-схемами инструментов. `loaders/prompt_loader.py` — ре-экспорт.
- **tools/**: `ToolRegistry` — 16 схем из `tools/list` (fallback — `definitions.py`)
  + обёртка `tutu_mcp`; `to_prompt_context()` отдаёт схемы в промпт.
- **skills/**: сценарии-группировки инструментов (BaseSkill/SkillResult).

## Интерфейсы (interfaces/)
- **cli.py** — консоль: создаёт SyncMCPClient → ToolRegistry → PromptLoader →
  OpenAIAgent; команды /help /clear /tools /logs /exit; логи в файл (DEBUG), в консоль — только UX.
- **dependencies.py** — `AppDependencies`: lifespan-инициализация AsyncMCPClient, реестра, промпта и AsyncOpenAIAgent для FastAPI.
- **api/** — REST `POST /chat`, `GET /health`, `GET /tools` + WS `/ws` (текст/голос).

## Поток данных (консоль)
main.py → cli.py → agent.run() → [LLM ⇄ tools] → SyncMCPClient → mcp.tutu.ru →
результат → mcp_result_to_text → LLM → финальный ответ → print в консоль.

## Принципы
- Сервер (MCP) изолирован в клиентах; агент не знает JSON-RPC.
- Инструменты описаны в одном месте (registry); промпты — в одном месте (prompts/).
- Дата и правила параметров — данные промпта, а не код агента.
- Тест `main_tests.py` — эталон сигнатур: правки схем начинаются с него.


Структура папок тома Windows 11
Серийный номер тома: 3A28-7A4A
C:.
|   .env
|   .env.example
|   .gitignore
|   agentss_create.md
|   draft01.md
|   logs.txt
|   main.py
|   main_tests.py
|   MCP_description.md
|   mcp_server_check_report.json
|   PRESENTATION.md
|   README.md
|   requirements.txt
|   run_api.py
|   setup.ps1
|   
+---.vscode
|   |   settings.json
|   |   
|   \---excel-pq-symbols
|           excel-pq-symbols.json
|           
+---agents
|   |   builder.py
|   |   orchestrator.py
|   |   specs.py
|   |   __init__.py
|   |   
|   +---prompts
|   |   |   mcp_instructions.md
|   |   |   mcp_tools_rules.md
|   |   |   prompt_loader.py
|   |   |   travel_assistant.md
|   |   |   __init__.py
|   |   |   
|   |   \---__pycache__
|   |           loader.cpython-313.pyc
|   |           prompt_loader.cpython-313.pyc
|   |           __init__.cpython-313.pyc
|   |           
|   +---skills
|   |       avia.md
|   |       consultant.md
|   |       hotels.md
|   |       rail.md
|   |       SKILLS_CATALOG.md
|   |       __init__.py
|           
+---client
|   |   base.py
|   |   client_llm.py
|   |   handlers.py
|   |   openai_agent.py
|   |   openai_responses_agent.py
|   |   session.py
|   |   __init__.py
|   |   
|   \---__pycache__
|           base.cpython-313.pyc
|           handlers.cpython-313.pyc
|           openai_agent.cpython-313.pyc
|           realtime_agent.cpython-313.pyc
|           responses_agent.cpython-313.pyc
|           session.cpython-313.pyc
|           __init__.cpython-313.pyc
|           
+---config
|   |   settings.py
|   |   __init__.py
|   |   
|   \---__pycache__
|           settings.cpython-313.pyc
|           __init__.cpython-313.pyc
|           
+---interfaces
|   |   cli.py
|   |   dependencies.py
|   |   __init__.py
|   |   
|   +---api
|   |   |   app.py
|   |   |   routes.py
|   |   |   websocket.py
|   |   |   __init__.py
|   |   |   
|   |   \---__pycache__
|   |           app.cpython-313.pyc
|   |           routes.cpython-313.pyc
|   |           websocket.cpython-313.pyc
|   |           __init__.cpython-313.pyc
|   |           
|   +---web
|   |       index.html
+---knowledge_base
|       faq_tutu.md
|       travel_hacks.md
|       
+---tests
|   |   test_agent_creation.py
|   |   test_mcp_server.py
|   |   voice_agent.py
|   |   __init__.py
|           
\---tools
    |   definitions.py
    |   registry.py
    |   __init__.py
    |   
    +---mcp
    |   |   async_client.py
    |   |   models.py
    |   |   sync_client.py
    |   |   __init__.py


Отличная структура! Проект выглядит очень грамотно и модульно. Пока `main.py` запускается и тестируется, вот готовое описание архитектуры в формате Markdown. 

Можешь сохранить этот текст как `ARCHITECTURE.md` или вставить в `README.md`.

---

# 🏗 Архитектура проекта: Tutu Travel Agent (Multi-Agent)

Проект реализован по модульной архитектуре с разделением на ядро (агенты), инфраструктуру (MCP/LLM клиенты), конфигурацию и интерфейсы взаимодействия (CLI/API).

## 📁 Корневая директория
*   `main.py` — Главная точка входа в приложение. Парсит аргументы командной строки и запускает нужный режим (консольный чат или FastAPI сервер).
*   `run_api.py` — Альтернативный скрипт для быстрого локального запуска только API-сервера (через Uvicorn).
*   `.env` / `.env.example` — Файлы конфигурации окружения (API ключи LLM, URL MCP-сервера, настройки портов).
*   `requirements.txt` — Список зависимостей Python (FastAPI, OpenAI, aiohttp, PyYAML и др.).
*   `setup.ps1` — Скрипт автоматической настройки окружения для PowerShell.
*   `logs.txt` — Файл логов работы агентов (генерируется автоматически).
*   `*.md` (`README`, `PRESENTATION`, `draft01` и др.) — Документация, черновики промптов и отчеты о тестировании MCP.

---

## 🧠 `agents/` — Ядро мультиагентной системы
Здесь живет логика оркестрации и сборки специалистов.
*   `orchestrator.py` — **Оркестратор (Роутер)**. Принимает запрос пользователя, анализирует его с помощью легковесной LLM и решает, какому именно специалисту (агенту) передать задачу. Поддерживает контекст диалога.
*   `builder.py` — **Сборщик агентов (AgentBuilder)**. Фабрика, которая лениво (по требованию) собирает конкретного агента: подтягивает нужные MCP-инструменты, загружает системный промпт и специфичную инструкцию (skill). Общие ресурсы (клиенты) кэшируются.
*   `specs.py` — **Спецификации (AgentSpec)**. Dataclass-описания команды агентов (имя, роль, какие скиллы использует, температура генерации). Здесь задается состав команды (`DEFAULT_TEAM`).
*   `__init__.py` — Делает папку пакетом Python, экспортирует главные классы.

### 📂 `agents/prompts/` — Системные промпты
*   `prompt_loader.py` — Загрузчик промптов. Читает `.md` файлы, добавляет динамическую шапку с текущей датой/временем и склеивает их в единый системный промпт.
*   `travel_assistant.md` — Базовая роль и тон общения ассистента.
*   `mcp_instructions.md` — Общие правила работы с внешними инструментами.
*   `mcp_tools_rules.md` — Строгие правила вызова функций (формат JSON, обработка ошибок).

### 📂 `agents/skills/` — Доменные знания (Skills)
Текстовые инструкции для конкретных специалистов в формате Markdown с YAML-заголовками (стандарт OpenClaw).
*   `SKILLS_CATALOG.md` — Каталог всех навыков. Используется Роутером для понимания, какой агент за что отвечает.
*   `rail.md` — Инструкция и список инструментов для специалиста по Ж/Д билетам.
*   `avia.md` — Инструкция для специалиста по Авиабилетам.
*   `hotels.md` — Инструкция для специалиста по Отелям.
*   `consultant.md` — Инструкция для мульти-транспортного консультанта (сложные маршруты).

---

## 🔌 `client/` — Клиенты LLM и управление сессиями
Обертки над API нейросетей и логика диалогов.
*   `base.py` — Базовый абстрактный класс агента.
*   `client_llm.py` — Фабрика/обертка для создания клиентов LLM (OpenAI/YandexGPT).
*   `openai_agent.py` — Реализация агента, работающего через стандартный Chat Completions API (с циклом вызова tools).
*   `openai_responses_agent.py` — Реализация агента под новый Responses API.
*   `handlers.py` — Обработчики ответов от нейросети (парсинг `function_call`, выполнение MCP-запроса, возврат результата в LLM).
*   `session.py` — Менеджер сессий. Хранит историю сообщений (`messages`) для каждого пользователя, чтобы агенты помнили контекст.

---

## ⚙️ `config/` — Конфигурация
*   `settings.py` — Singleton-класс настроек. Читает переменные из `.env`, валидирует их и предоставляет удобный доступ ко всем параметрам приложения (URL, ключи, лимиты токенов).

---

## 🖥 `interfaces/` — Точки взаимодействия с пользователем
*   `cli.py` — **Консольный интерфейс**. Интерактивный чат в терминале с поддержкой команд (`/help`, `/clear`, `/tools`).
*   `dependencies.py` — **Dependency Injection (DI)** для FastAPI. Управляет жизненным циклом приложения: при старте поднимает асинхронные клиенты, при остановке — корректно их закрывает.

### 📂 `interfaces/api/` — Web API (FastAPI)
*   `app.py` — Инициализация FastAPI приложения, настройка CORS, подключение роутеров и раздача веб-интерфейса.
*   `routes.py` — REST эндпоинты (`POST /chat` для текстовых запросов, `GET /health`).
*   `websocket.py` — WebSocket эндпоинты:
    *   `/ws` — Текстовый чат в реальном времени.
    *   `/ws/voice` — Голосовой режим (Push-to-Talk). Проксирует аудио из браузера напрямую в Yandex Realtime API и выполняет MCP-инструменты на лету.

### 📂 `interfaces/web/`
*   `index.html` — Легкий фронтенд (веб-чат) для тестирования API и голосового режима прямо в браузере.

---

## 🛠 `tools/` — Инфраструктура инструментов (MCP)
Связь с внешним миром (сервер Туту).
*   `registry.py` — **Реестр инструментов**. Хранит список доступных функций в формате, понятном для OpenAI API. Умеет загружать инструменты динамически из MCP-сервера или статически из файла.
*   `definitions.py` — Статические определения инструментов (fallback, если MCP-сервер недоступен).

### 📂 `tools/mcp/` — MCP Клиенты
*   `sync_client.py` — Синхронный клиент Model Context Protocol (используется в консольном режиме CLI).
*   `async_client.py` — Асинхронный клиент MCP (используется в FastAPI и WebSocket, чтобы не блокировать сервер).
*   `models.py` — Pydantic-модели для типизации запросов и ответов MCP-сервера.

---

##  `knowledge_base/` — База знаний
Статические текстовые файлы, которые могут подгружаться в промпты для расширения кругозора агента.
*   `faq_tutu.md` — Частые вопросы и ответы службы поддержки.
*   `travel_hacks.md` — Полезные советы для путешественников.

---

## 🧪 `tests/` — Тесты
*   `test_agent_creation.py` — Юнит-тесты проверки сборки агентов и роутера.
*   `test_mcp_server.py` — Интеграционные тесты подключения к MCP-серверу Туту.
*   `voice_agent.py` — Скрипт для ручного тестирования голосового WebSocket-потока.

---

*(Жду результатов запуска `main.py`! Если вылезут ошибки с импортами или пробелами — кидай traceback, быстро починим).*