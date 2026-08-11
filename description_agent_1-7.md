Пайплайн прохождения кода — Tutu Travel Agent
Мультиагентный туристический ассистент на базе Yandex LLM + MCP-сервера Туту. Ниже — полный разбор пайплайна, функций, методов и оценка качества.

1. Точки входа (Entry Points)
Проект имеет два способа запуска:

main.py — универсальная точка входа
parse_args() — парсит CLI: --mode (console/api/websocket), --host, --port, --api-type (openai/responses).
run_console() — делегирует в interfaces/cli.py.
run_api() — запускает uvicorn с FastAPI-приложением.
main() — диспетчер режимов.
run_api.py — упрощённый запуск только API (порт из настроек).
2. Пайплайн консольного режима (основной путь)
main.py:run_console()
  └─ interfaces/cli.py:chat_loop()
       ├─ setup_logging()          — файл(DEBUG) + консоль(WARNING)
       ├─ settings.validate_llm()  — проверка API-ключа и folder_id
       ├─ specs = DEFAULT_TEAM     — 4 специалиста (rail/avia/hotels/general)
       ├─ Orchestrator(specs)      — создаётся, агенты НЕ создаются (лениво)
       ├─ Session()                — контейнер истории
       └─ while True:  (цикл ввода)
            ├─ обработка команд /help /clear /tools /logs /exit
            └─ orchestrator.run(user_input, session.history, last_agent)
                 ├─ _route()        — лёгкий LLM-вызов: выбор специалиста
                 ├─ _get_agent()    — ленивое создание агента через AgentFactory
                 └─ agent.run()     — агентный цикл «модель→tools→модель»
Шаг 2.1 — Роутинг Orchestrator._route()
Формирует список специалистов из AgentSpec.description.
Делает один LLM-вызов с temperature=0.0, max_tokens=16.
Ищет имя специалиста в ответе; при ошибке/несовпадении — fallback на last_agent или general.
Использует LLMClientFactory.get_client() — кэшированный OpenAI-клиент.
Шаг 2.2 — Ленивое создание агента Orchestrator._get_agent()
Кэширует агентов в self._agents (создаётся один раз на сессию).
Вызывает AgentFactory.build().
Шаг 2.3 — Сборка агента AgentFactory.build()
Получает LLM-клиент, модель (spec.model или settings.composite_model).
get_mcp() — лениво создаёт SyncMCPClient (инициализирует MCP-сессию).
get_registry() — загружает инструменты из MCP (list_tools) или статический fallback.
_resolve_tools() — фильтрует инструменты по скилу специалиста (skill_tools).
Выбирает класс: ResponsesAgent (если api_type="responses") или OpenAIAgent.
Системный промпт собирает PromptLoader.get_system_prompt() из travel_assistant.md + mcp_instructions.md + mcp_tools_rules.md + шапки с текущей датой.
Шаг 2.4 — Агентный цикл BaseAgent.run()
Цикл до max_iterations (по умолчанию 12):

_api_messages() — добавляет свежий system prompt (через _get_system_prompt(), поддерживает callable-provider).
_chat_sync() — один запрос к LLM → LLMStep.
Если есть tool_calls:
_assistant_tool_calls_message() — формирует assistant-сообщение с tool_calls.
_run_one_tool_sync() → _execute_tool_sync() → SyncMCPClient.call_tool().
mcp_result_to_text() — форматирует результат для модели (добавляет системные подсказки при пустых offers/variants).
_tool_result_message() — добавляет tool-результат в историю.
continue (следующая итерация).
Если tool_calls нет — финальный ответ. При пустом ответе после tool calls — _retry_empty_sync().
Превышение итераций → предупреждение.
Шаг 2.5 — MCP-вызов SyncMCPClient.call_tool()
Строит JSON-RPC 2.0 запрос через build_tool_call_request().
_post() — HTTP POST с заголовком Mcp-Session-Id, обработкой таймаутов/ошибок.
_parse_response() — разбирает JSON или SSE (text/event-stream).
Инициализация: initialize() → _send_initialized_notification().
3. Пайплайн API-режима (FastAPI)
run_api.py → interfaces/api/app.py:app
  ├─ lifespan() → AppDependencies.startup()
  │    ├─ AsyncMCPClient.initialize()
  │    ├─ ToolRegistry.load_from_mcp() / load_static()
  │    ├─ PromptLoader.get_system_prompt()
  │    └─ AsyncOpenAIAgent(...)
  ├─ POST /chat → routes.chat()
  │    ├─ SessionStore.get_or_create()
  │    ├─ agent.run_async() → AsyncOpenAIAgent.run_async()
  │    └─ сохранение сессии
  ├─ GET /health, GET /tools
  ├─ WS /ws → websocket_endpoint() (текстовый чат)
  └─ WS /ws/voice → websocket_voice() (голосовой прокси в Yandex Realtime)
Асинхронный агентный цикл AsyncOpenAIAgent.run_async()
Аналогичен синхронному, но await self.client.chat.completions.create() и await self.mcp.call_tool().
AsyncMCPClient.call_tool() (async_client.py) — гибкая сигнатура: поддерживает новый стиль (tool_name, args), (tool_name, args, session=...) и legacy (session, tool_name, args). Создаёт собственную aiohttp-сессию лениво.
Голосовой режим websocket_voice()
Проксирует PCM16-аудио в Yandex Realtime API.
Два параллельных task: client_to_yandex() и yandex_to_client().
При function_call вызывает handle_function_call() → mcp_client.call_tool() → отправляет результат обратно.
4. Ключевые классы и их методы
Класс	Файл	Ключевые методы
Orchestrator	orchestrator.py	run(), _route(), _get_agent(), team
AgentFactory	factory.py	build(), get_mcp(), get_registry(), _resolve_tools()
BaseAgent	base.py	run(), run_async(), stream(), _chat_sync/async, _execute_tool_sync/async, mcp_result_to_text(), normalize_tool_arguments(), llm_step_from_openai()
OpenAIAgent / AsyncOpenAIAgent	openai_agent.py	run(), run_async(), _parse_tool_call(), _retry_empty_response()
ResponsesAgent / AsyncResponsesAgent	responses_agent.py	run(), run_async(), _parse_tool_call()
SyncMCPClient	sync_client.py	initialize(), list_tools(), call_tool(), _post(), _parse_response()
AsyncMCPClient	async_client.py	initialize(), list_tools(), call_tool(), _get_session()
ToolRegistry	registry.py	load_static(), load_from_mcp(), tool_names(), to_prompt_context()
PromptLoader	prompt_loader.py	get_system_prompt(), compose(), default_variables()
LLMClientFactory	client_factory.py	get_client(), clear()
Session / SessionStore	session.py	add_message(), clear(), history, to_dict(), get_or_create()
Settings	settings.py	api_key, composite_model, validate_llm()
AppDependencies	dependencies.py	startup(), shutdown()
5. Оценка качества кода
✅ Сильные стороны
Чистая архитектура с разделением ответственности. Чёткое разделение: interfaces (CLI/API/WS), agent (логика), config, knowledge_base. Слои изолированы.
Паттерн «Шаблонный метод» в BaseAgent. Общий цикл вынесен в базу, подклассы реализуют только 4 тонких метода (_chat_sync/async, _execute_tool_sync/async). Это хороший дизайн.
Ленивая инициализация. Агенты, MCP-клиент, реестр инструментов создаются по требованию и кэшируются — экономия ресурсов.
Кэширование. LLMClientFactory (thread-safe через Lock), PromptLoader._cache, SyncMCPClient._tools_cache, get_settings() через lru_cache.
Устойчивость к ошибкам. Обработка таймаутов, connection errors, JSON/SSE парсинга, retry при пустом ответе, fallback роутера.
Хорошее логирование. Детальные debug-логи в файл, WARNING+ в консоль, логирование tool calls с размером результата.
Типизация. from __future__ import annotations, dataclasses (AgentSpec, LLMStep, ToolCallInfo), pydantic Settings.
Документация. Подробные docstrings и комментарии (особенно в responses_agent.py, async_client.py).
⚠️ Слабые стороны и проблемы
Дублирование кода (главная проблема). Агентный цикл реализован 4 раза: в BaseAgent.run(), OpenAIAgent.run(), AsyncOpenAIAgent.run_async(), ResponsesAgent.run(), AsyncResponsesAgent.run_async(). При этом OpenAIAgent и ResponsesAgent не используют цикл из BaseAgent, а дублируют его. Это нарушает DRY и усложняет поддержку. BaseAgent.run() фактически мёртвый код для этих подклассов.
OpenAIAgent.run_async() делегирует синхронному run() (openai_agent.py:227) — блокирует event loop в FastAPI. Это серьёзный баг производительности в асинхронном контексте.
AsyncOpenAIAgent.run() бросает NotImplementedError — но BaseAgent.stream() вызывает run_async(), что ок, однако контракт неоднороден.
Опечатка в дефолте cli.py:102: api_type: str = "opena,i" — неверное значение по умолчанию (запятая). Хотя main() передаёт "openai", это скрытый дефект.
Несоответствие сигнатур. PromptLoader.__init__ в factory.py:26 вызывается без аргументов, а в dependencies.py:59 — с settings=self.settings, но PromptLoader.__init__ принимает prompts_dir, а не settings. Это молча игнорируется (лишний kwarg), но указывает на рассинхрон.
ToolRegistry(use_wrapper=True) в dependencies.py:35 — параметр use_wrapper не существует в ToolRegistry.__init__ (принимает только self). Лишний аргумент, который молча отбрасывается.
app.py использует ws_router (app.py:53), но импортирует только api_router. ws_router не импортирован — это NameError при запуске API. (Возможно, есть неявный импорт, но в прочитанном коде его нет.)
Settings не использует pydantic env-механизм — все значения читаются через os.environ в default_factory. Работает, но теряет преимущества pydantic (валидация, типы из env).
mcp_headers в Settings — статический dict, не читается из env, хотя SyncMCPClient ожидает заголовки авторизации. Возможна проблема с реальной авторизацией.
SessionStore без очистки по TTL — get_or_create удаляет просроченные сессии только при обращении, но нет фоновой очистки (утечка памяти при долгой работе).
BaseAgent содержит и sync, и async циклы — дублирование логики внутри одного класса (хотя и с общими хелперами).
_retry_empty_response дублируется в OpenAIAgent, AsyncOpenAIAgent, ResponsesAgent, AsyncResponsesAgent — 4 копии одного метода.
📊 Итоговая оценка
Критерий	Оценка
Архитектура / разделение слоёв	9/10
Читаемость и документация	8/10
Обработка ошибок	8/10
DRY (отсутствие дублирования)	4/10
Консистентность API	5/10
Производительность (async)	5/10
Тестируемость	6/10
Общая оценка	6.5/10
Рекомендации:

Устранить дублирование агентного цикла — оставить единый цикл в BaseAgent, а подклассы должны реализовывать только _chat_* и _execute_tool_*. Удалить дублирующие run()/run_async() из OpenAIAgent/ResponsesAgent.
Исправить OpenAIAgent.run_async() — реализовать настоящий async, а не делегировать синхронному.
Исправить опечатку "opena,i" в cli.py:102.
Исправить импорт ws_router в app.py.
Синхронизировать сигнатуры PromptLoader и ToolRegistry с местами вызова.
Добавить фоновую очистку SessionStore по TTL.
Использовать pydantic env-механизм для настроек вместо ручного os.environ.