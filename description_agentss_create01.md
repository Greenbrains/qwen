# Разбор `chat_loop` с оркестратором

## Что происходит на этом участке кода

```python
def chat_loop(settings=None, api_type: str = "openai") -> int:
    settings = settings or get_settings()
    log = setup_logging(settings)
    settings.validate_llm()

    # 1️⃣ Берём готовую "команду" специалистов
    specs = DEFAULT_TEAM
    if api_type == "responses":
        # Для каждого спека меняем api_type на "responses"
        specs = [dataclasses.replace(s, api_type="responses") for s in DEFAULT_TEAM]

    # 2️⃣ Создаём оркестратор (он НЕ создаёт агентов здесь — только запоминает specs)
    orchestrator = Orchestrator(specs, settings=settings)

    # 3️⃣ Сессия, счётчики, приветствие
    session = Session()
    last_tool_calls: List = []
    last_agent: Optional[str] = None

    print(f"🤖 Модель: {settings.composite_model}")
    print(f"🔌 API: {api_type}")
    print(f"👥 Команда: {', '.join(orchestrator.team)}")  # ← список имён
    print(f"📝 Логи: {os.path.abspath(settings.log_file)}")
    print_banner()
```

**Главное**: здесь **не создаётся ни одного агента**. Создаются только **описания** (specs), которые оркестратор будет использовать позже.

---

## Где живут specs и скилы

### 📁 `agent/specs.py` — команда специалистов

```python
DEFAULT_TEAM: List[AgentSpec] = [
    AgentSpec(
        name="rail",
        description="Поезда дальнего следования и электрички: расписание, вагоны, места, билеты",
        skill="rail",   # ← имя скила
    ),
    AgentSpec(
        name="avia",
        description="Авиабилеты: рейсы, тарифы, багаж, пересадки, бронирование",
        skill="avia",
    ),
    AgentSpec(
        name="hotels",
        description="Отели: подбор по датам, питанию, рейтингу и бюджету, бронирование",
        skill="hotels",
    ),
    AgentSpec(
        name="general",
        description="Общие и смешанные запросы: мультимодальные «как добраться», транспорт + отель сразу",
        skill="full",   # ← видит ВСЕ инструменты
    ),
]
```

Каждый `AgentSpec` — это «паспорт» специалиста:
- **name** — короткое имя (`rail`, `avia`, `hotels`, `general`)
- **description** — текстовое описание для роутера (чтобы LLM выбирала)
- **skill** — имя набора инструментов (см. ниже)
- опционально: `model`, `temperature`, `prompt_id` и т.д.

### 📁 `agent/core/skills/definitions.py` — наборы инструментов

```python
SKILLS = {
    "rail": {
        "tools": [
            "search_rail", "search_etrain",
            "get_rail_instructions", "get_etrain_instructions",
            "get_rail_seatmap",
            "get_offer_details", "create_checkout_link", "fetch_resource",
        ],
    },
    "avia": {
        "tools": [
            "search_avia", "get_avia_instructions",
            "get_offer_details", "create_checkout_link", "fetch_resource",
        ],
    },
    "hotels": {
        "tools": [
            "search_hotels", "get_hotels_instructions",
            "get_offer_details", "create_checkout_link", "fetch_resource",
        ],
    },
    # "full" отсутствует — значит, все инструменты реестра
}
```

**Логика скилов**:
- `skill="rail"` → агент видит **только** инструменты из `SKILLS["rail"]`
- `skill="full"` → агент видит **все** 16 инструментов реестра

**Зачем это нужно**: если специалист по поездам видит `search_hotels`, он может начать галлюцинировать и вызывать его в неподходящий момент. Ограничив набор, мы делаем каждого агента узким и предсказуемым.

---

## Как создаются агенты: ленивая фабрика

### Поток создания

```
chat_loop()
    │
    ├── 1. specs = DEFAULT_TEAM  ← только описания, 4 объекта AgentSpec
    │
    └── 2. Orchestrator(specs, settings=settings)
              │
              ├── сохраняет specs в self._specs = {"rail": ..., "avia": ..., ...}
              ├── создаёт AgentFactory (один раз, общий для всех агентов)
              │     │
              │     ├── lazily создаёт SyncMCPClient  (один клиент на всех)
              │     ├── lazily создаёт ToolRegistry   (грузит 16 tools с MCP)
              │     └── lazily создаёт PromptLoader   (читает md-промпты)
              │
              └── self._agents = {}   ← ПУСТОЙ СЛОВАРЬ!
                                         Агентов ещё НЕТ.
```

### Момент создания агента

Агент создаётся **только когда роутер его выбрал**:

```python
# В orchestrator.py:
def run(self, user_input, history, last_agent=None):
    name = self._route(user_input, last_agent)  # ← роутер выбрал, напр., "rail"
    agent = self._get_agent(name)               # ← здесь создаётся агент
    return agent.run(user_input, history)

def _get_agent(self, name):
    if name not in self._agents:
        logger.info(f"🏗️  Создаю агента [{name}]")
        self._agents[name] = self._factory.build(self._specs[name])
    return self._agents[name]
```

### Что делает `factory.build(spec)`

```python
def build(self, spec: AgentSpec):
    client = LLMClientFactory.get_client(self._settings)  # общий клиент
    model = spec.model or self._settings.composite_model
    
    # 🔑 Ключевой шаг: РЕЖЕМ tools по скилу
    common = dict(
        client=client,
        model=model,
        mcp_client=self.get_mcp(),
        tools=self._resolve_tools(spec),  # ← фильтр инструментов
        max_iterations=spec.max_iterations,
        temperature=spec.temperature,
        max_tokens=spec.max_tokens,
    )
    
    if spec.api_type == "responses":
        return ResponsesAgent(prompt_id=..., **common)
    return OpenAIAgent(system_prompt=self._loader.get_system_prompt(), **common)

def _resolve_tools(self, spec):
    registry = self.get_registry()
    allowed = skill_tools(spec.skill)   # ← список имён из SKILLS
    if allowed is None:                 # skill="full"
        return registry.tools           # все 16 инструментов
    names = set(allowed)
    return [t for t in registry.tools if t["function"]["name"] in names]
```

---

## Сколько агентов создаётся за сессию?

**Максимум 4** (по числу специалистов в команде), но часто меньше.

| Сценарий | Создано агентов |
|---|---|
| «Найди билеты Москва–Омск» → rail отвечает до конца | 1 (`rail`) |
| «Найди билеты, потом подбери отель в Омске» | 2 (`rail` + `hotels`) |
| «Посмотри отели и электрички и самолёты» | 3 (`hotels` + `rail` + `avia`) |
| Смешанный запрос → general | 1 (`general`) |

**Агенты переиспользуются**: если роутер второй раз выберет `rail`, фабрика вернёт уже созданного агента из `self._agents["rail"]`.

### Ресурсы, общие для всех агентов

| Ресурс | Количество | Где создаётся |
|---|---|---|
| `SyncMCPClient` | **1** | `factory.get_mcp()` |
| `ToolRegistry` | **1** (все 16 инструментов) | `factory.get_registry()` |
| `openai.OpenAI` клиент | **1** (кэш по credentials) | `LLMClientFactory.get_client()` |
| `PromptLoader` | **1** | `factory._loader` |
| **Экземпляры `OpenAIAgent`** | до 4 | `factory.build()` при первом обращении |

---

## `dataclasses.replace` — зачем

```python
specs = DEFAULT_TEAM
if api_type == "responses":
    specs = [dataclasses.replace(s, api_type="responses") for s in DEFAULT_TEAM]
```

`DEFAULT_TEAM` по умолчанию имеет `api_type="openai"`. Когда пользователь запускает `--api-type responses`, мы не мутируем оригинал (он может использоваться где-то ещё), а создаём **копии** с другим значением `api_type`:

```python
# Было:
AgentSpec(name="rail", ..., api_type="openai")

# Стало:
AgentSpec(name="rail", ..., api_type="responses")
```

`dataclasses.replace` — это как `dict.copy()` + обновление полей. Без этого все спеки ссылались бы на один и тот же объект.

---

## Роутер — как выбирается специалист

В `Orchestrator._route()` один лёгкий LLM-вызов:

```python
_ROUTER_PROMPT = """\
Ты — роутер запросов туристического ассистента.
Выбери РОВНО ОДНОГО специалиста для запроса пользователя.
Ответь одним словом — именем специалиста, без пояснений.

Специалисты:
- rail: Поезда дальнего следования и электрички...
- avia: Авиабилеты...
- hotels: Отели...
- general: Общие и смешанные запросы...

Запрос пользователя: найди электричку Москва-Калуга
Имя специалиста:"""

# → ответ: "rail"
```

**Параметры роутера**:
- `temperature=0.0` — детерминированный выбор
- `max_tokens=16` — только слово
- **НЕ видит** инструментов и историю — только описания специалистов

**Fallback**: если роутер упал или вернул неизвестное имя → `last_agent` (тот же специалист продолжает диалог) или `general`.

---

## Визуально всё вместе

```
Запуск: python main.py --mode console
    │
    ├── chat_loop()
    │    ├── specs = [rail, avia, hotels, general]  ← 4 описания
    │    ├── orchestrator = Orchestrator(specs)     ← агентов пока 0
    │    └── print "👥 Команда: rail, avia, hotels, general"
    │
    └── while True:
         user_input = "найди электричку Москва-Калуга"
              │
              ├── orchestrator.run(user_input, history, last_agent)
              │    │
              │    ├── _route() → LLM: "rail"  (1 лёгкий вызов)
              │    │
              │    ├── _get_agent("rail")
              │    │    └── factory.build(AgentSpec(name="rail", skill="rail"))
              │    │         ├── client (общий)
              │    │         ├── tools = SKILLS["rail"] → 8 инструментов
              │    │         └── system_prompt = travel_assistant + mcp_instructions + mcp_tools_rules
              │    │         └── return OpenAIAgent(...)  ← СОЗДАН первый агент
              │    │
              │    └── agent.run(user_input, history)
              │         └── цикл tool calls (search_etrain, ...)
              │              └── return ответ + history
              │
              └── last_agent = "rail"  (запомним для следующего запроса)
```

На следующем запросе «оформи билет на 14:07» роутер снова выберет `rail` → агент переиспользуется из `self._agents["rail"]`. А вот «посмотри отель в Калуге» переключит на `hotels` — создастся второй агент с другим набором инструментов.

---

## Как добавить нового специалиста

1. **Опишите скил** в `agent/core/skills/definitions.py`:
   ```python
   SKILLS["bus"] = {
       "tools": ["search_bus", "get_bus_instructions", 
                 "get_offer_details", "create_checkout_link"],
   }
   ```

2. **Добавьте спека** в `DEFAULT_TEAM` в `agent/specs.py`:
   ```python
   AgentSpec(
       name="bus",
       description="Автобусные билеты: междугородние рейсы, расписание, бронирование",
       skill="bus",
   )
   ```

3. Готово — роутер автоматически увидит нового специалиста и начнёт его выбирать.

Код `chat_loop`, `orchestrator`, `factory` — **ничего менять не нужно**.