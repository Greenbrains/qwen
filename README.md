# 🧳 Travel Assistant `minibu` v1.0

Консольный мультиагентный ИИ-ассистент туроператора, работающий через
**MCP-сервер Туту** (`https://mcp.tutu.ru/mcp`) и **Yandex AI Studio**
(OpenAI-совместимый API).

Проект реализует архитектуру **Orchestrator → Executor**: роутер выбирает
подходящий навык, а исполнитель с ограниченным набором инструментов выполняет
задачу пользователя. Данные отделены от кода: промпты в YAML, навыки в Markdown,
секреты в `.env`.

---

## 🚀 Варианты запуска

| Как запускаешь | Что происходит |
| :--- | :--- |
| **Двойной клик** по `start.bat` | Открывается меню `[1] CLI / [2] API / [3] WEB` |
| `.\start.bat` + ввод `1` | Консольный чат |
| `.\start.bat cli` | Сразу консольный чат (без меню) |
| `.\start.bat api` | API-сервер на порту **8000** |
| `.\start.bat api 9000` | API-сервер на порту **9000** |
| `.\start.bat web` | Веб-режим + автоматически откроется браузер |
| `.\start.bat web 3000` | Веб-режим на порту **3000** |

---

## 🎯 Возможности

- **Подбор путешествий**: авиа, ЖД, автобусы, электрички, отели через MCP Туту
- **Маркетинговые задачи**: SEO, копирайтинг, анализ конкурентов, ICP
- **Экономия токенов**: прокси `tutu_call` вместо 16 отдельных схем (~90% экономии)
- **Мультиагентность**: оркестратор на дешёвой модели, исполнитель на мощной
- **Полный трейсинг**: DEBUG в `logs.txt`, INFO в консоль, подсчёт токенов за сессию

---

## 🏗 Архитектура и Workflow

### Схема взаимодействия

```
┌──────────────┐
│   main.py    │  точка входа: CLI-цикл
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│  Orchestrator    │  менеджер сессии
└──────┬───────────┘
       │
       ├──► Router Agent (aliceai-llm-flash)
       │    └─ читает .agents/skills/SKILL.md
       │    └─ возвращает имя навыка: "touragent"
       │
       ├──► load_skill("touragent")
       │    └─ читает .agents/skills/touragent/touragent.md
       │
       ├──► SKILL_TOOLSETS["touragent"]
       │    └─ фильтр инструментов из реестра
       │
       └──► Executor Agent (qwen3.6-35b-a3b)
            ├─ системный промпт (YAML + навык + дата + MCP-каталог)
            ├─ tool-calling loop
            └─ вызывает tutu_call → SyncMCPClient → mcp.tutu.ru
```

### Пошаговый Workflow одного запроса

1. **Пользователь** пишет запрос в CLI (`main.py`).
2. **`main.py`** вызывает `orchestrator.route_and_execute(user_message, history)`.
3. **Router Agent** (`BaseAgent` + модель `aliceai-llm-flash/latest`):
   - Получает простой системный промпт «ты роутер».
   - Возвращает одно слово: `touragent`, `marketingskills` или `general`.
4. **Orchestrator** загружает инструкцию навыка:
   - `load_skill("touragent")` → читает `.agents/skills/touragent/touragent.md`.
5. **Orchestrator** фильтрует инструменты:
   - `SKILL_TOOLSETS["touragent"]` = `["load_skill", "tutu_call", "file_write", "file_read"]`.
   - Исполнитель получит **только** эти инструменты, а не все 16+ схем.
6. **PromptLoader** собирает финальный системный промпт:
   - База из `.agents/prompts/system.yaml`.
   - Блок с текущей датой (`YYYY-MM-DD` + день недели).
   - Каталог инструментов Туту (строится из `mcp_client.list_tools()`).
   - Инструкция навыка.
7. **Executor Agent** (`BaseAgent` + модель `qwen3.6-35b-a3b/latest`):
   - Входит в цикл tool-calling (до 10 итераций).
   - Вызывает `tutu_call(tool="search_avia", args_json='{...}')`.
   - `tutu_call` делает пред-валидацию аргументов по JSON-схеме MCP.
   - `SyncMCPClient` отправляет JSON-RPC запрос на `https://mcp.tutu.ru/mcp`.
   - Результат возвращается в историю диалога.
8. **Итог**: Executor формирует финальный ответ в Markdown.
9. **UsageTracker** аккумулирует токены и время, выводит сводку:
   ```
   📊 Сессия: 8 запросов | ⏱️ 44.46s | 🔤 58577 in / 7141 out / 65718 total
   ```

---

## 📁 Структура проекта

```
ft_assistant2026/
│
├── main.py                          # 🚪 Точка входа CLI
├── .env                             # 🔑 Секреты (YANDEX_API_KEY, FOLDER_ID)
├── requirements.txt                 # 📦 Зависимости
├── logs.txt                         # 📝 DEBUG-трейс работы
├── output/                          # 📂 Артефакты (файлы, изображения)
│
├── config/
│   ├── __init__.py                  # экспорт Settings, get_settings
│   └── settings.py                  # ⚙️ Pydantic-settings (переменные + дефолты)
│
├── agent/                           # 🤖 Ядро мультиагентной системы
│   ├── base.py                      # BaseAgent + UsageTracker (tool-calling loop)
│   ├── orchestrator.py              # 🧭 Оркестратор (Router + spawn Executor)
│   │
│   └── core/
│       ├── mcp/
│       │   ├── sync_client.py       # SyncMCPClient (SSE, TTL-кэш, авто-retry)
│       │   └── tutu_tools.py        # tutu_call + tutu_catalog_markdown
│       │
│       ├── prompts/
│       │   └── loader.py            # PromptLoader (YAML + дата + навык + MCP)
│       │
│       └── tools/
│           ├── agent_tools.py       # @tool, load_skill, bash_execute, YandexTools
│           └── registry.py          # ToolRegistry (сборка всех инструментов)
│
├── interfaces/
│   └── api/                         # (на будущее) FastAPI / WebSocket
│
└── .agents/                         # 📚 ДАННЫЕ агента (не код!)
    ├── prompts/
    │   └── system.yaml              # Системный промпт + параметры генерации
    └── skills/
        ├── SKILL.md                 # 📋 КАТАЛОГ навыков (читает Router)
        ├── touragent/
        │   └── touragent.md         # Инструкция турагента
        └── marketingskills/
            └── marketingskills.md   # Инструкция маркетолога
```

---

## 🔄 Как расширить навыки

Добавление нового навыка **не требует изменения кода** — только данные.

### Шаг 1. Создать папку и файл навыка

```bash
mkdir -p .agents/skills/financeagent
touch .agents/skills/financeagent/financeagent.md
```

### Шаг 2. Написать инструкцию в Markdown

Файл `.agents/skills/financeagent/financeagent.md`:

```markdown
# Навык: Финансовый аналитик

## Описание
Анализ финансовых данных, построение отчётов, графики.

## Когда использовать
- «Построй график продаж по месяцам»
- «Проанализируй CSV-файл с выручкой»

## Рабочий процесс
1. Загрузи данные через `file_read` или `upload_file`.
2. Построй анализ через `execute_code` (Code Interpreter).
3. Сохрани результат через `file_write`.
```

### Шаг 3. Добавить навык в каталог

Файл `.agents/skills/SKILL.md` — добавить строку в таблицу:

```markdown
| Название навыка | skill_name | Когда использовать |
| --- | --- | --- |
| Турагент | touragent | Подбор путешествий... |
| Маркетинг | marketingskills | Продуктовый маркетинг... |
| Финансы | financeagent | Анализ финансовых данных... |  ← НОВАЯ СТРОКА
```

### Шаг 4. Прописать набор инструментов

Файл `agent/core/tools/agent_tools.py` → словарь `SKILL_TOOLSETS`:

```python
SKILL_TOOLSETS = {
    "touragent": ["load_skill", "tutu_call", "file_write", "file_read"],
    "marketingskills": ["load_skill", "web_search", "execute_code", ...],
    "financeagent": ["load_skill", "execute_code", "file_read", "file_write", 
                     "upload_file", "download_file", "list_files"],  ← НОВАЯ ЗАПИСЬ
    "general": [...],
}
```

**Всё!** Router сам увидит новую строку в `SKILL.md` и будет маршрутизировать
запросы на новый навык, а Executor получит только разрешённые инструменты.

---

## 🚀 Установка и запуск

```bash
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Создать .env (шаблон):
# YANDEX_API_KEY=AQVN...
# YANDEX_FOLDER_ID=b1gd...
# YANDEX_MODEL_ROUTER=aliceai-llm-flash/latest
# YANDEX_MODEL_AGENT=qwen3.6-35b-a3b/latest

# 3. Запустить
python main.py
```

### Команды CLI

| Команда | Действие |
| :--- | :--- |
| `/clear` | Очистить историю диалога |
| `/usage` | Показать статистику токенов за сессию |
| `/exit` или `Ctrl+C` | Выход |

---

## 💰 Экономия токенов

| Метод | Эффект |
| :--- | :--- |
| **`tutu_call` (прокси)** | 1 схема вместо 16 → ~90% экономии на schemas |
| **`SKILL_TOOLSETS`** | Executor получает только нужные инструменты |
| **`aliceai-llm-flash` для роутера** | 0.1₽/1k in вместо 0.8₽/1k in (в 8× дешевле Pro) |
| **Пред-валидация args** | Ловит ошибки ДО запроса к MCP |
| **`view="compact"` в навыках** | Меньше данных в ответах `get_offer_details` |

**Типичная стоимость сессии** (8-10 запросов, ~65k токенов):
- Роутер: ~0.01 ₽
- Executor: ~15-20 ₽
- **Итого: ~15-20 ₽**

---

## 🐛 Troubleshooting

| Симптом | Решение |
| :--- | :--- |
| `Failed to get model` | Проверь имя модели в `.env` (например `aliceai-llm-flash`, а не `alice-llm-flash`) |
| MCP не подключается | Проверь доступность `https://mcp.tutu.ru/mcp` |
| Модель галлюцинирует параметры | Читай `tutu_catalog_markdown` в системном промпте — там точные поля |
| 400 Bad Request на API | Модель требует `gpt://{folder_id}/{model}` URI — это делает `base.py` автоматически |

---

## 📚 Дальнейшее развитие

- [ ] `interfaces/api/` — FastAPI + WebSocket (web-интерфейс)
- [ ] `interfaces/telegram/` — Telegram-бот
- [ ] Лимит истории (`MAX_HISTORY_TURNS`)
- [ ] Truncate ответов MCP (>4000 символов)
- [ ] Кэширование системного промпта (prompt caching)
- [ ] Стоимость в ₽ в `UsageTracker`

---

**Версия:** `minibu v1.0 (CLI)` | **Дата:** 19 августа 2026 | **Модели:** Yandex AI Studio

## 💡 Что добавить в следующий коммит (v1.1)?

🔍 Анализ логов: что можно улучшить

#### ✅ Что работает хорошо:

- Роутер на `aliceai-llm-flash/latest` — **69+3 токена**, очень быстро и дёшево
- Пред-валидация в `tutu_call` ловит ошибки до сервера (экономит round-trip)
- `tutu_call` корректно вызывает MCP и получает данные

#### ⚠️ Проблемы для будущего (не блокируют коммит):

1. **Гигантские ответы MCP**: `search_avia` вернул **38 371 символ**, `search_hotels` — **19 396**. Это кладётся в историю и на следующем шаге модель получает 29 000 токенов контекста.
2. **Сумма сессии**: 89 674 in / 7 240 out = ~97k токенов. При цене Qwen3.6 это **~20₽ за сессию**.
3. **Нет лимита истории** — на 5-м запросе история уже 10+ сообщений.

**Решения на будущее** (не для этого коммита):

- Truncate результатов MCP до 4000 символов
- `MAX_HISTORY_TURNS=5` в orchestrator
- Кэширование системного промпта

Когда захочешь бороться с расходом токенов:

1. **Truncate MCP ответов** в `agent/core/mcp/tutu_tools.py`:

   ```python
   MAX_RESULT_CHARS = 4000
   result = mcp_client.call_tool(tool, args)
   if len(result) > MAX_RESULT_CHARS:
       result = result[:MAX_RESULT_CHARS] + "\n\n[... обрезано, полные данные в логах ...]"
   ```

2. **MAX_HISTORY_TURNS** в `orchestrator.py`:

   ```python
   history = history[-10:]  # последние 10 сообщений
   ```

Это снизит стоимость сессии с 20₽ до ~8-10₽.
