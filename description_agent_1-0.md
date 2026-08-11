# 🚆 Tutu Travel Agent

Интеллектуальный туристический ассистент на базе Yandex AI Studio (модель Qwen 3.6 35B‑A3B) и MCP‑сервера Туту.
Агент решает реальные задачи путешественников: подбор мультимодальных маршрутов (поезд + самолёт + автобус),
умное сравнение отелей, схемы вагонов с выбором места и готовые ссылки на бронирование.
Работает с текстом (консоль, REST API) и голосом (WebSocket Realtime API).

**Ключевые свойства:**
- Модель **не галлюцинирует** цены/даты/наличие мест — все факты берутся только из живого MCP‑сервера.
- В системный промпт при старте сессии **инжектится текущая дата** — «завтра» всегда означает реальное завтра.
- Строгие схемы параметров 16 инструментов зафиксированы в промптах и проверены автотестом (`main_tests.py`, 16/16 ✅).

## ✨ Возможности
- 🔍 Поиск билетов: авиа, ж/д (РЖД), автобусы, электрички
- 🏨 Поиск отелей с фильтрами (звёзды, питание, бюджет, удобства)
- 🗺️ Мультимодальные маршруты «как добраться» одним запросом
- 💺 Схемы вагонов с точным расположением и типами мест
- 🛒 Ссылки на бронирование (deeplink с предзаполненной корзиной)
- 🧠 Автоматическое чтение плейбуков перед каждым доменом поиска
- 📅 Осведомлённость о текущей дате (относительные даты: «завтра», «на следующей неделе»)
- 💬 Контекстный диалог с историей; 🎙️ голосовой режим; 🌐 REST API

## 🏗 Структура проекта

```
travel_assistant2026/
├── main.py                     # Точка входа (--mode console|api|websocket)
├── main_tests.py               # Полный чек MCP-сервера: 16 инструментов
├── run_api.py                  # Быстрый запуск FastAPI (uvicorn)
├── config/
│   ├── __init__.py
│   └── settings.py             # Settings (pydantic), get_settings(), .env
├── agent/
│   ├── base.py                 # BaseAgent — общий агентный цикл (sync + async)
│   ├── openai_agent.py         # OpenAIAgent / AsyncOpenAIAgent (тонкие подклассы)
│   ├── realtime_agent.py       # RealtimeAgent — голосовой режим (WebSocket)
│   ├── handlers.py             # handle_function_call для Realtime API
│   ├── session.py              # Session, SessionStore (история диалога)
│   └── core/
│       ├── mcp/
│       │   ├── sync_client.py  # SyncMCPClient (requests) — консоль
│       │   ├── async_client.py # AsyncMCPClient (aiohttp) — FastAPI/WS
│       │   ├── checkout_helper.py # Распаковка checkout_ref для create_checkout_link
│       │   └── models.py       # Pydantic-модели JSON-RPC 2.0
│       ├── prompts/            # ВСЕ промпты проекта
│       │   ├── loader.py       # PromptLoader: Jinja2 + автоинъекция даты
│       │   ├── system_prompt.jinja # Главный шаблон: блок даты + include md + схемы
│       │   ├── travel_assistant.md # Роль, стиль, workflow, карточки ответов
│       │   ├── mcp_instructions.md # Подключение и типовые ловушки
│       │   └── mcp_tools_rules.md  # Строгие схемы параметров 16 инструментов
│       ├── tools/
│       │   ├── registry.py     # ToolRegistry (из MCP tools/list или статика)
│       │   └── definitions.py  # Статические схемы + обёртка tutu_mcp
│       ├── loaders/            # config_loader, prompt_loader (ре-экспорт)
│       ├── skills/             # BaseSkill, пример скила
│       └── models/             # yandexgpt_config.json
├── interfaces/
│   ├── __init__.py
│   ├── cli.py                  # Консольный чат (команды /help /clear /tools /logs)
│   ├── dependencies.py         # DI для FastAPI (lifespan-инициализация)
│   ├── api/                    # FastAPI-приложение
│   │   ├── __init__.py
│   │   ├── app.py              # Создание app (lifespan, роутеры)
│   │   ├── routes.py           # REST: POST /chat, GET /health, GET /tools
│   │   ├── websocket.py        # WebSocket /ws (текстовый чат)
│   │   └── realtime_ws.py      # WebSocket Yandex Realtime (голос)
│   ├── web/
│   │   └── index.html          # Веб-страница чата (статика)
│   ├── knowledge_base/         # База знаний (FAQ и советы)
│   │   ├── faq_tutu.md         # FAQ Tutu
│   │   └── travel_hacks.md     # Travel-хаки
│   └── tests/                  # Тесты и проверочные скрипты
│       ├── __init__.py
│       ├── test_agent_creation.py # Тест создания агента
│       ├── test_mcp_server.py     # Тест MCP-сервера
│       └── voice_agent.py         # Скрипт голосового агента (ручная проверка)
├── .env                        # Локальные переменные (не коммитить)
├── .env.example                # Шаблон переменных окружения
├── .gitignore
├── requirements.txt
├── README.md
├── PRESENTATION.md             # Презентация проекта
├── MCP_description.md          # Описание MCP-сервера и инструментов
├── mcp_server_check_report.json # Отчёт main_tests.py по MCP-серверу
├── draft01.md                  # Черновые заметки
└── logs.txt                    # Логи

```


## 🧠 Как работает агент
Как это теперь работает
main.py --mode console
   └→ cli.chat_loop → Orchestrator.run(запрос, история)
         ├→ роутер (1 лёгкий вызов, temperature=0) → имя специалиста
         ├→ AgentFactory.build(spec) лениво (MCP и реестр — один раз на всех)
         └→ специалист (rail/avia/hotels/general) со своим набором tools

В консоли увидите 🤖 Агент [rail]: ... — сразу видно, кто отвечал. Подсказка last_agent держит диалог на том же специалисте («оформи билет» после поиска электричек не уйдёт на general).
Запуск: python main.py --mode console. Если в логе снова появится tutu_mcp — значит, на этой машине не заменился registry.py (файл №1).

### Агентный цикл (`agent/base.py`)

Запрос пользователя
↓
system-промпт (свежая дата) + история + user
↓
Qwen 3.6 (OpenAI-совместимый API Yandex, tools = 16 схем + обёртка)
↓
есть tool_calls? ──да──▶ нормализация аргументов (поддержка обёртки
│ {"tool_name": …, "arguments": {…}}) → MCP-вызов →
│ текст результата → обратно в модель (до N итераций)
нет
↓
финальный ответ пользователю

- `BaseAgent` содержит весь общий цикл; подклассы реализуют только 4 тонких метода:
  `_chat_sync/_chat_async` (один запрос к LLM) и `_execute_tool_sync/_execute_tool_async` (один MCP‑вызов).
- При пустом финальном ответе после tool calls — автоматический retry с просьбой сформулировать ответ.
- Ограничение цикла — `max_agent_iterations` (по умолчанию 12).

### Системный промпт и дата (`agent/core/prompts/`)
- `PromptLoader.get_system_prompt()` рендерит `system_prompt.jinja` **в момент старта сессии**:
  блок «СЕГОДНЯ / ЗАВТРА / текущий год» (свежие значения на каждый рендер) +
  `{% include %}` трёх md‑файлов + JSON‑схемы инструментов из реестра.
- Благодаря этому «найди на завтра билет» всегда уходит с корректной датой (например, `2026-08-05`),
  а правила параметров (`origin/destination`, без `passengers` в поиске и т.д.) зашиты в `mcp_tools_rules.md`.

### MCP‑клиенты (`agent/core/mcp/`)
- Протокол: Streamable HTTP (JSON‑RPC 2.0), сервер `https://mcp.tutu.ru/mcp`, без авторизации.
- Рукопожатие: `initialize` → `notifications/initialized` → `tools/list` (16 инструментов).
- Заголовки: `Accept: application/json, text/event-stream`, `MCP-Protocol-Version: 2024-11-05`.
- Ответы парсятся и как JSON, и как SSE (`data:`‑строки); `Mcp-Session-Id` сохраняется из заголовков.
- Таймауты: 30 c на init/list, 120 c на `tools/call` (долгие поиски).

### Бронирование (checkout)
Поля `checkout_ref` из ответа поиска передаются в `create_checkout_link`
**распакованными на верхний уровень** arguments (схема сервера запрещает вложенный объект):

json
{ "product_type": "rail", "passengers": 1,
"transport": "railway", "departure_city_id": 2657260, "…": "все поля checkout_ref" }

Хелпер — `agent/core/mcp/checkout_helper.py`.

### Защита от пустых результатов
`BaseAgent.mcp_result_to_text()` добавляет в текст результата системную подсказку,
если `offers`/`variants` пусты, — агент обязан сообщить пользователю и предложить альтернативы.

## 🔌 Инструменты MCP (16)

| Категория | Инструменты | Корректные параметры |
|---|---|---|
| Поиск | `search_avia` | `origin`, `destination`, `departure_date`, опц. `return_date`, `adults/children/infants` |
| | `search_rail`, `search_bus`, `search_etrain` | `origin`, `destination`, `departure_date` (БЕЗ `passengers`) |
| | `search_multitransport` | `origin`, `destination`, `departure_date`, `adults`, `optimize_for` |
| | `search_hotels` | `city_name`, `check_in`, `check_out` (БЕЗ `guests`) |
| Плейбуки | `get_*_instructions` ×6 | аргументов не требуют; читаются перед первым поиском домена |
| Детализация | `get_offer_details` | `product_type` + `details_ref` (объект из поиска), опц. `view` |
| | `get_rail_seatmap` | `details_ref` + `car_number` **строкой** ("1") |
| Действия | `create_checkout_link` | `product_type` + `passengers` (число) + поля `checkout_ref` на верхнем уровне |
| Ресурсы | `fetch_resource` | `uri`, напр. `tutu://amenities/dictionary` |

Подробный справочник с примерами — в `MCP_description.md`.

## 🚀 Быстрый старт
```bash
pip install -r requirements.txt
cp .env.example .env            # указать API-ключ и YANDEX_FOLDER_ID

python main.py --mode console   # интерактивный чат
python main.py --mode api       # FastAPI: POST /chat, GET /health, GET /tools, WS /ws

🧪 Команды чата и тесты
Команда
Действие
/help /clear /tools /logs /exit
справка / очистка истории / последние MCP‑вызовы / хвост logs.txt / выход

python main_tests.py   # живой чек всех 16 инструментов MCP (эталон сигнатур)

📝 Логирование
Технические логи — logs.txt (уровень DEBUG: payload запросов, превью ответов, итерации цикла).
В консоль выводятся только UX‑сообщения и предупреждения.
📞 Контакты
MCP‑сервер: https://mcp.tutu.ru/mcp · Yandex AI Studio: https://aistudio.yandex.ru