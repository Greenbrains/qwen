# Декоратор `@tool` для YandexGPT (OpenAI-compatible API)

Да, конечно! Вот полноценная реализация декоратора, который автоматически превращает обычные Python-функции в инструменты с JSON-схемой для function calling.

## 📄 `tools.py` — Декоратор и инфраструктура

```python
import inspect
import json
from typing import get_type_hints, get_origin, get_args, Annotated
from functools import wraps
from pathlib import Path
import os


# ============================================================
# 1. Декоратор @tool 
# ============================================================

def tool(func=None, *, name: str = None, description: str = None):
    """
    Декоратор для превращения обычной функции в инструмент для LLM.
    Автоматически извлекает имя, описание и схему параметров из type hints.
    """
    def decorator(fn):
        tool_name = name or fn.__name__
        tool_description = description or (fn.__doc__ or "").strip()
        parameters_schema = _extract_parameters_schema(fn)
        
        tool_schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": parameters_schema
            }
        }
        
        fn._tool_schema = tool_schema
        fn._tool_name = tool_name
        
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        
        wrapper._tool_schema = tool_schema
        wrapper._tool_name = tool_name
        return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


def _extract_parameters_schema(fn) -> dict:
    """Извлекает JSON-схему параметров из сигнатуры функции."""
    sig = inspect.signature(fn)
    
    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception:
        hints = {}
    
    properties = {}
    required = []
    
    for param_name, param in sig.parameters.items():
        if param_name in ('self', 'cls', 'client'):
            continue
        
        param_type = hints.get(param_name, str)
        param_description = ""
        actual_type = param_type
        
        if hasattr(param_type, '__metadata__'):
            actual_type = param_type.__args__[0]
            if param_type.__metadata__:
                param_description = param_type.__metadata__[0]
        
        json_type = _python_type_to_json(actual_type)
        prop_schema = {"type": json_type}
        if param_description:
            prop_schema["description"] = param_description
        
        properties[param_name] = prop_schema
        
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    
    return schema


def _python_type_to_json(python_type) -> str:
    """Преобразует Python тип в JSON Schema тип."""
    origin = get_origin(python_type)
    if origin is not None:
        args = get_args(python_type)
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _python_type_to_json(non_none_args[0])
    
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }
    
    return type_map.get(python_type, "string")


def collect_tools(*tool_functions) -> list:
    """Собирает список JSON-схем всех инструментов."""
    return [fn._tool_schema for fn in tool_functions if hasattr(fn, '_tool_schema')]


def create_tool_router(*tool_functions) -> dict:
    """Создаёт словарь {имя_инструмента: функция}."""
    return {
        fn._tool_name: fn
        for fn in tool_functions
        if hasattr(fn, '_tool_name')
    }


# ============================================================
# 2. Базовые инструменты 
# ============================================================

@tool
def load_skill(
    skill_name: Annotated[str, "Имя навыка, например 'cloudru-vm' или 'browser-use'"]
) -> str:
    """Загружает содержимое навыка из файла .agents/skills/<name>/<name>.md"""
    skill_path = Path(f".agents/skills/{skill_name}/{skill_name}.md")
    
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return f"❌ Навык '{skill_name}' не найден"


@tool
def bash_execute(
    command: Annotated[str, "Bash-команда для выполнения"]
) -> str:
    """Выполняет bash-команду локально и возвращает stdout/stderr."""
    import subprocess
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return result.stdout or "✅ Выполнено успешно"
        return f"❌ Ошибка (код {result.returncode}):\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "❌ Превышено время выполнения (60 секунд)"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"


@tool
def file_read(
    file_path: Annotated[str, "Путь к локальному файлу для чтения"]
) -> str:
    """Читает содержимое локального файла."""
    path = Path(file_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"❌ Файл не найден: {file_path}"


@tool
def file_write(
    file_path: Annotated[str, "Путь к локальному файлу для записи"],
    content: Annotated[str, "Содержимое для записи"]
) -> str:
    """Записывает содержимое в локальный файл."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"✅ Файл сохранён: {file_path}"


# ============================================================
# 3. Дополнительные инструменты для Яндекс AI Studio
# ============================================================

class YandexTools:
    """Класс для инструментов, требующих клиент OpenAI."""
    
    def __init__(self, client):
        self.client = client
    
    @tool
    def upload_file(
        self,
        local_path: Annotated[str, "Путь к локальному файлу для загрузки в Яндекс AI Studio"],
        purpose: Annotated[str, "Назначение файла: 'user_data' для Code Interpreter, 'assistants' для Vector Store"]
    ) -> str:
        """Загружает файл в Яндекс AI Studio Files API и возвращает file_id."""
        path = Path(local_path)
        if not path.exists():
            return f"❌ Файл не найден: {local_path}"
        
        try:
            with open(path, "rb") as f:
                uploaded = self.client.files.create(
                    file=f,
                    purpose=purpose
                )
            return f"✅ Файл загружен:\n- Имя: {path.name}\n- File ID: {uploaded.id}\n- Размер: {uploaded.bytes} bytes"
        except Exception as e:
            return f"❌ Ошибка загрузки: {str(e)}"
    
    @tool
    def download_file(
        self,
        file_id: Annotated[str, "Идентификатор файла в Files API (например, 'fvt5ajp8l83v...')"],
        local_path: Annotated[str, "Локальный путь для сохранения файла"]
    ) -> str:
        """Скачивает файл из Яндекс AI Studio Files API по file_id."""
        try:
            file_content = self.client.files.content(file_id)
            
            path = Path(local_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'wb') as f:
                f.write(file_content.read())
            
            return f"✅ Файл скачан и сохранён: {local_path}"
        except Exception as e:
            return f"❌ Ошибка скачивания: {str(e)}"
    
    @tool
    def list_files(self) -> str:
        """Возвращает список всех загруженных файлов в Files API."""
        try:
            files = self.client.files.list()
            
            if not files.data:
                return "📭 Список файлов пуст"
            
            result = "📋 Загруженные файлы:\n"
            for file in files.data:
                result += f"- {file.filename} (ID: {file.id}, {file.bytes} bytes, создан: {file.created_at})\n"
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"
    
    @tool
    def execute_code(
        self,
        code: Annotated[str, "Python-код для выполнения в изолированном контейнере"],
        file_ids: Annotated[list, "Список file_id файлов, которые нужны для выполнения кода"] = None
    ) -> str:
        """Выполняет Python-код в изолированном контейнере Code Interpreter."""
        try:
            container_config = {
                "type": "auto"
            }
            
            if file_ids:
                container_config["file_ids"] = file_ids
            
            response = self.client.responses.create(
                model=f"gpt://{os.getenv('YANDEX_FOLDER_ID')}/{os.getenv('YANDEX_MODEL', 'qwen3-235b-a22b-fp8')}",
                instructions="Выполни этот Python-код и верни результат",
                input=code,
                tools=[{
                    "type": "code_interpreter",
                    "container": container_config
                }]
            )
            
            result_parts = []
            
            for item in response.output:
                if item.type == "code_interpreter_call":
                    result_parts.append(f"Код:\n{item.code}\n")
                    for output_item in item.outputs:
                        if output_item.logs:
                            result_parts.append(f"Вывод:\n{output_item.logs}")
                
                elif item.type == "message":
                    for content in item.content:
                        if content.type == "output_text":
                            result_parts.append(f"Ответ: {content.text}")
                        
                        if hasattr(content, 'annotations') and content.annotations:
                            for annotation in content.annotations:
                                if annotation.type == "container_file_citation":
                                    result_parts.append(
                                        f"📎 Создан файл: {annotation.filename} (ID: {annotation.file_id})"
                                    )
            
            return "\n\n".join(result_parts) if result_parts else "✅ Код выполнен (без вывода)"
        
        except Exception as e:
            return f"❌ Ошибка выполнения: {str(e)}"
    
    @tool
    def generate_image(
        self,
        prompt: Annotated[str, "Текстовое описание изображения для генерации"],
        size: Annotated[str, "Размер изображения: '1024x1024', '1536x1024' или '1024x1536'"]
    ) -> str:
        """Генерирует изображение по текстовому описанию."""
        try:
            response = self.client.responses.create(
                model=f"gpt://{os.getenv('YANDEX_FOLDER_ID')}/{os.getenv('YANDEX_MODEL', 'yandexgpt/latest')}",
                input=prompt,
                tools=[{
                    "type": "image_generation",
                    "size": size
                }]
            )
            
            result_parts = []
            
            for item in response.output:
                if item.type == "image_generation_call":
                    result_parts.append(f"✅ Изображение сгенерировано")
                    result_parts.append(f"- Статус: {item.status}")
                    result_parts.append(f"- File ID: {item.file_id}")
                    result_parts.append(f"- Размер base64: {len(item.result)} символов")
                    result_parts.append(f"\nИспользуйте download_file с file_id={item.file_id} для сохранения")
                
                elif item.type == "message":
                    for content in item.content:
                        if content.type == "output_text":
                            result_parts.append(f"\nКомментарий: {content.text}")
            
            return "\n".join(result_parts) if result_parts else "❌ Изображение не сгенерировано"
        
        except Exception as e:
            return f"❌ Ошибка генерации: {str(e)}"
    
    @tool
    def use_mcp_server(
        self,
        server_url: Annotated[str, "URL MCP-сервера (SSE endpoint)"],
        server_label: Annotated[str, "Краткое имя сервера для идентификации"],
        description: Annotated[str, "Описание возможностей сервера"],
        require_approval: Annotated[str, "Политика безопасности: 'always' (требовать подтверждение) или 'never' (автоматически)"]
    ) -> str:
        """Подключает MCP-сервер для расширения возможностей агента."""
        try:
            # MCP-инструмент передаётся в tools при создании response
            # Здесь мы просто возвращаем конфигурацию для использования
            mcp_config = {
                "type": "mcp",
                "server_url": server_url,
                "server_label": server_label,
                "description": description,
                "require_approval": require_approval
            }
            
            return f"✅ Конфигурация MCP-сервера создана:\n{json.dumps(mcp_config, indent=2, ensure_ascii=False)}\n\nДобавьте эту конфигурацию в tools при следующем вызове API"
        
        except Exception as e:
            return f"❌ Ошибка создания конфигурации: {str(e)}"


# ============================================================
# 4. Утилиты для сбора инструментов и диспетчеризации
# ============================================================

def create_all_tools(client=None):
    """Создаёт список всех инструментов."""
    basic_tools = [load_skill, bash_execute, file_read, file_write]
    
    if client:
        yandex_tools = YandexTools(client)
        advanced_tools = [
            yandex_tools.upload_file,
            yandex_tools.download_file,
            yandex_tools.list_files,
            yandex_tools.execute_code,
            yandex_tools.generate_image,
            yandex_tools.use_mcp_server
        ]
        return basic_tools + advanced_tools
    
    return basic_tools
```

---

##  `agent.py` — Агент с YandexGPT

```python
import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tools import create_all_tools, collect_tools, create_tool_router

load_dotenv()

# ============================================================
# Конфигурация Яндекс AI Studio
# ============================================================

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt/latest")

# Создаём клиент OpenAI для работы с Яндекс AI Studio (совместимый API)
client = OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID
)

# Создаём все инструменты
ALL_TOOLS = create_all_tools(client)
TOOLS_SCHEMA = collect_tools(*ALL_TOOLS)
TOOL_ROUTER = create_tool_router(*ALL_TOOLS)

# Системный промпт агента
SYSTEM_PROMPT = """Ты — мощный агент-исполнитель с доступом к Яндекс AI Studio.

## Твои возможности
1. **Навыки (Skills)** — загружай и выполняй навыки из .agents/SKILL.md
2. **Локальное выполнение** — bash-команды, чтение/запись файлов
3. **Code Interpreter** — выполняй Python-код в изолированном контейнере
4. **Files API** — загружай и скачивай файлы в облачное хранилище
5. **Image Generation** — генерируй изображения по описанию
6. **MCP Servers** — подключай внешние сервисы через MCP-протокол

## Рабочий процесс
1. Анализируй запрос пользователя
2. Определи, какой инструмент лучше всего подходит
3. Если нужен навык — загрузи его через load_skill
4. Если нужен сложный код — используй execute_code
5. Если нужны файлы — используй upload_file/download_file
6. Если нужна визуализация — используй generate_image

## Правила
- НЕ выводи секретные ключи в чат
- Спрашивай подтверждение перед деструктивными операциями
- Для сложных задач разбивай работу на шаги
- Всегда сообщай пользователю, что ты делаешь
"""


# ============================================================
# Основной цикл агента
# ============================================================

def chat_with_agent(user_message: str, conversation_history: list = None):
    """Отправляет сообщение агенту и обрабатывает вызовы инструментов."""
    
    if conversation_history is None:
        conversation_history = []
    
    if not conversation_history:
        conversation_history.append({
            "role": "system",
            "content": SYSTEM_PROMPT
        })
    
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    print("🤖 Агент думает...\n")
    
    # Максимум 10 итераций для предотвращения бесконечного цикла
    max_iterations = 10
    
    for iteration in range(max_iterations):
        # Запрос к модели
        response = client.chat.completions.create(
            model=f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
            messages=conversation_history,
            tools=TOOLS_SCHEMA if TOOLS_SCHEMA else None,
            tool_choice="auto" if TOOLS_SCHEMA else None,
            temperature=0.3,
            max_tokens=2000
        )
        
        message = response.choices[0].message
        
        # Если модель не хочет вызывать инструменты — возвращаем ответ
        if not message.tool_calls:
            conversation_history.append({
                "role": "assistant",
                "content": message.content
            })
            return message.content, conversation_history
        
        # Добавляем ответ модели с tool_calls в историю
        conversation_history.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [tc.model_dump() for tc in message.tool_calls]
        })
        
        # Выполняем каждый вызов инструмента
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            
            print(f"🔧 Вызов инструмента: {func_name}({func_args})")
            
            if func_name in TOOL_ROUTER:
                try:
                    # Передаём client для инструментов YandexTools
                    if 'client' in TOOL_ROUTER[func_name].__code__.co_varnames:
                        result = TOOL_ROUTER[func_name](client=client, **func_args)
                    else:
                        result = TOOL_ROUTER[func_name](**func_args)
                    result_text = str(result)
                except Exception as e:
                    result_text = f"❌ Ошибка выполнения: {str(e)}"
            else:
                result_text = f"❌ Инструмент '{func_name}' не найден"
            
            print(f"   → Результат: {result_text[:100]}...\n")
            
            conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_text
            })
    
    return "❌ Превышено максимальное количество итераций", conversation_history


# ============================================================
# Интерактивный режим
# ============================================================

def interactive_mode():
    """Интерактивный режим работы с агентом."""
    print("=" * 60)
    print("🚀 Агент с Яндекс AI Studio запущен")
    print("=" * 60)
    print("Доступные инструменты:")
    for tool_func in ALL_TOOLS:
        if hasattr(tool_func, '_tool_name'):
            print(f"  • {tool_func._tool_name}")
    print("=" * 60)
    print("Введите 'exit' для выхода\n")
    
    history = []
    
    while True:
        user_input = input("👤 Вы: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'выход']:
            print("👋 До свидания!")
            break
        
        if user_input:
            response, history = chat_with_agent(user_input, history)
            print(f"\n🤖 Агент:\n{response}\n")


# ============================================================
# Примеры использования
# ============================================================

def example_code_interpreter():
    """Пример использования Code Interpreter."""
    print("\n" + "=" * 60)
    print("📊 Пример: Code Interpreter")
    print("=" * 60)
    
    code = """
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, label='sin(x)')
plt.title('График функции sin(x)')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True)
plt.savefig('sin_plot.png')
print('График сохранён в sin_plot.png')
"""
    
    response, _ = chat_with_agent(
        f"Выполни этот Python-код:\n{code}",
        []
    )
    
    print(f"\nРезультат:\n{response}\n")


def example_file_upload():
    """Пример загрузки файла."""
    print("\n" + "=" * 60)
    print("📁 Пример: Загрузка файла")
    print("=" * 60)
    
    # Создаём тестовый файл
    test_file = Path("test_data.csv")
    test_file.write_text("name,value\nitem1,100\nitem2,200\nitem3,300")
    
    response, _ = chat_with_agent(
        f"Загрузи файл test_data.csv в Files API с purpose='user_data'",
        []
    )
    
    print(f"\nРезультат:\n{response}\n")


def example_image_generation():
    """Пример генерации изображения."""
    print("\n" + "=" * 60)
    print("🎨 Пример: Генерация изображения")
    print("=" * 60)
    
    response, _ = chat_with_agent(
        "Сгенерируй изображение серого кота, обнимающего выдру, размер 1024x1024",
        []
    )
    
    print(f"\nРезультат:\n{response}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
        
        if example == "code":
            example_code_interpreter()
        elif example == "file":
            example_file_upload()
        elif example == "image":
            example_image_generation()
        else:
            print(f"Неизвестный пример: {example}")
            print("Доступные: code, file, image")
    else:
        interactive_mode()
```

---

## 📄 `.env` — Переменные окружения

```env
YANDEX_API_KEY=your_yandex_api_key_here
YANDEX_FOLDER_ID=your_folder_id_here
```

---

## 🧪 Пример использования декоратора

### Простой вариант (docstring как описание):

```python
@tool
def search_web(query: str) -> str:
    """Ищет информацию в интернете по запросу."""
    # реализация
    ...
```

### Продвинутый вариант (Annotated для описания параметров):

```python
@tool
def search_web(
    query: Annotated[str, "Поисковый запрос, например 'погода в Москве'"],
    max_results: Annotated[int, "Максимальное количество результатов (по умолчанию 5)"] = 5
) -> str:
    """Ищет информацию в интернете и возвращает список релевантных страниц."""
    # реализация
    ...
```

### Кастомное имя и описание:

```python
@tool(name="web_search", description="Поиск в интернете через Яндекс")
def my_search_function(query: str) -> str:
    """Этот docstring будет проигнорирован, используется description из декоратора."""
    ...
```

---

##  Что генерирует декоратор

Для функции:

```python
@tool
def bash_execute(
    command: Annotated[str, "Bash-команда для выполнения"]
) -> str:
    """Выполняет bash-команду и возвращает stdout/stderr."""
    ...
```

Декоратор автоматически создаёт:

```json
{
  "type": "function",
  "function": {
    "name": "bash_execute",
    "description": "Выполняет bash-команду и возвращает stdout/stderr.",
    "parameters": {
      "type": "object",
      "properties": {
        "command": {
          "type": "string",
          "description": "Bash-команда для выполнения"
        }
      },
      "required": ["command"]
    }
  }
}
```

---

## ✅ Преимущества подхода

1. **Минимум кода** — просто пишете обычную Python-функцию с type hints
2. **Автоматическая схема** — декоратор сам генерирует JSON для API
3. **Поддержка Annotated** — можно давать описания параметрам
4. **Универсальность** — работает с любым OpenAI-compatible API (YandexGPT, GigaChat, OpenAI, локальные модели через Ollama/vLLM)
5. **Лёгкая диспетчеризация** — `create_tool_router` создаёт словарь для вызова функций по имени

Теперь добавление нового инструмента — это просто написание функции с декоратором `@tool`! 🎉