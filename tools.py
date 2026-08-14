"""
📋 Что включено в этот файл
1. Декоратор
@tool, _extract_parameters_schema, _python_type_to_json, collect_tools, create_tool_router
2. Базовые инструменты
load_skill, bash_execute, file_read, file_write
3. YandexTools
Класс с методами для Files API, Code Interpreter, Image Generation, MCP
4. Фабрика
create_all_tools для удобной инициализации

"""


import inspect
import json
from typing import get_type_hints, get_origin, get_args, Annotated
from functools import wraps
from pathlib import Path
from datetime import datetime
import os
import re

# ============================================================
# 1. Декоратор @tool — превращает функции в инструменты для LLM
# ============================================================

def tool(func=None, *, name: str = None, description: str = None):
    """
    Декоратор для превращения обычной функции в инструмент для LLM.
    Автоматически извлекает имя, описание и схему параметров из type hints.
    
    Использование:
        @tool
        def my_func(x: int) -> str:
            '''Описание функции'''
            ...
        
        @tool(name="custom_name", description="Кастомное описание")
        def my_func(x: Annotated[int, "Описание параметра"]) -> str:
            ...
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
        fn._tool_description = tool_description
        
        @wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        
        wrapper._tool_schema = tool_schema
        wrapper._tool_name = tool_name
        wrapper._tool_description = tool_description
        
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
        
        # Обработка Annotated[type, "описание"]
        if hasattr(param_type, '__metadata__'):
            actual_type = param_type.__args__[0]
            if param_type.__metadata__:
                param_description = param_type.__metadata__[0]
        
        json_type = _python_type_to_json(actual_type)
        prop_schema = {"type": json_type}
        if param_description:
            prop_schema["description"] = param_description
        
        properties[param_name] = prop_schema
        
        # Параметр обязателен, если нет значения по умолчанию
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
        # Обработка Optional[X] = Union[X, None]
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
    """Собирает список JSON-схем всех инструментов для передачи в API."""
    return [fn._tool_schema for fn in tool_functions if hasattr(fn, '_tool_schema')]


def create_tool_router(*tool_functions) -> dict:
    """Создаёт словарь {имя_инструмента: функция} для диспетчеризации вызовов."""
    return {
        fn._tool_name: fn
        for fn in tool_functions
        if hasattr(fn, '_tool_name')
    }


# ============================================================
# 2. Базовые инструменты (локальное выполнение)
# ============================================================

# Корневая папка со навыками и файл-каталог (роутер).
SKILLS_ROOT = Path(".agents/skills")
SKILLS_CATALOG_FILE = SKILLS_ROOT / "SKILL.md"


def load_skills_catalog() -> str:
    """Возвращает текст каталога навыков (роутер) для показа агенту.

    Каталог — единственный источник правды о том, какие навыки есть и когда
    их применять. Агент читает его сам и выбирает навык; коду агента не нужно
    ничего знать о конкретных навыках.
    """
    if SKILLS_CATALOG_FILE.exists():
        return SKILLS_CATALOG_FILE.read_text(encoding="utf-8")
    # Фолбэк: если файла-каталога нет, собираем список из папок навыков.
    if SKILLS_ROOT.exists():
        names = sorted(p.name for p in SKILLS_ROOT.iterdir() if p.is_dir())
        if names:
            listing = "\n".join(f"- {n}" for n in names)
            return f"Обнаружены навыки (без описаний):\n{listing}"
    return "Каталог навыков пуст."


@tool
def load_skill(
    skill_name: Annotated[str, "Имя навыка из каталога, например 'cloudru-vm'. Оставь пустым, чтобы получить каталог всех навыков."] = ""
) -> str:
    """Загружает инструкцию навыка из .agents/skills/<name>/<name>.md.

    Если skill_name не указан — возвращает каталог доступных навыков (роутер),
    чтобы можно было выбрать подходящий. После загрузки навыка действуй строго
    по его тексту.
    """
    if not skill_name:
        return load_skills_catalog()

    skill_path = SKILLS_ROOT / skill_name / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")

    return (
        f"❌ Навык '{skill_name}' не найден. "
        f"Вызови load_skill() без аргумента, чтобы посмотреть доступные навыки."
    )


@tool
def bash_execute(
    command: Annotated[str, "Bash-команда для выполнения, например 'python vm.py list'"]
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
            return result.stdout or "✅ Выполнено успешно (без вывода)"
        return f"❌ Ошибка (код {result.returncode}):\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "❌ Превышено время выполнения (60 секунд)"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"


@tool
def file_read(
    file_path: Annotated[str, "Путь к локальному файлу для чтения"]
) -> str:
    """Читает содержимое локального файла и возвращает его текст."""
    path = Path(file_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"❌ Файл не найден: {file_path}"


@tool
def file_write(
    file_path: Annotated[str, "Путь к локальному файлу для записи"],
    content: Annotated[str, "Содержимое для записи в файл"]
) -> str:
    """Записывает содержимое в локальный файл, создавая директории при необходимости."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"✅ Файл сохранён: {file_path}"


# ============================================================
# 3. Инструменты для Яндекс AI Studio
# ============================================================

class YandexTools:
    """Класс для инструментов, требующих клиент OpenAI (для Яндекс AI Studio)."""
    
    def __init__(self, client):
        self.client = client
        # Создаём папку output в корне проекта для сохранения артефактов
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def _save_yandex_file(self, file_id: str, suggested_name: str = None) -> str:
        """
        Скачивает файл из Files API по file_id и сохраняет в папку output/.
        Возвращает относительный путь к файлу для использования в Markdown.
        """
        try:
            file_content = self.client.files.content(file_id)
            
            # Формируем уникальное имя файла
            if suggested_name:
                safe_name = Path(suggested_name).name
                filename = f"{Path(safe_name).stem}_{file_id[:8]}{Path(safe_name).suffix}"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"file_{timestamp}_{file_id[:8]}"
            
            local_path = self.output_dir / filename
            
            with open(local_path, 'wb') as f:
                f.write(file_content.read())
            
            # Возвращаем относительный путь с прямыми слэшами (для Markdown)
            return str(local_path).replace("\\", "/")
        
        except Exception as e:
            return f"ERROR: {str(e)}"
    
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
            return (
                f"✅ Файл загружен:\n"
                f"- Имя: {path.name}\n"
                f"- File ID: {uploaded.id}\n"
                f"- Размер: {uploaded.bytes} bytes"
            )
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
                result += (
                    f"- {file.filename} "
                    f"(ID: {file.id}, {file.bytes} bytes, создан: {file.created_at})\n"
                )
            
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"
    
    @tool
    def execute_code(
        self,
        code: Annotated[str, "Python-код для выполнения в изолированном контейнере"],
        file_ids: Annotated[list, "Список file_id файлов, которые нужны для выполнения кода"] = None
    ) -> str:
        """
        Выполняет Python-код в изолированном контейнере Code Interpreter.
        Все созданные файлы автоматически скачиваются в папку output/.

        ВАЖНО (свойство контейнера, а не подсказка к задаче):
        - Контейнер ИЗОЛИРОВАН ОТ СЕТИ: внутри execute_code нельзя ходить в
          интернет (никаких HTTP-запросов, скачиваний, обращений к API).
          Данные из сети получай отдельным инструментом web_search и передавай
          их в код как готовые значения.
        - Если коду нужна сторонняя библиотека, устанавливай её внутри самого
          кода перед импортом (pip доступен в контейнере).
        """
        try:
            container_config = {"type": "auto"}
            if file_ids:
                container_config["file_ids"] = file_ids
            
            response = self.client.responses.create(
                model=f"gpt://{os.getenv('YANDEX_FOLDER_ID')}/{os.getenv('YANDEX_MODEL', 'qwen3-235b-a22b-fp8')}",
                instructions="Выполни этот Python-код и верни результат",
                input=code,
                tools=[{"type": "code_interpreter", "container": container_config}]
            )
            
            result_parts = []
            downloaded_files = []
            
            for item in response.output:
                # Вывод кода и логов
                if item.type == "code_interpreter_call":
                    result_parts.append(f"```python\n{item.code}\n```")
                    for output_item in item.outputs:
                        if output_item.logs:
                            result_parts.append(f"**Вывод:**\n```\n{output_item.logs}\n```")
                
                # Текстовый ответ и аннотации с файлами
                elif item.type == "message":
                    for content in item.content:
                        if content.type == "output_text":
                            result_parts.append(content.text)
                        
                        # Скачиваем все файлы из аннотаций
                        if hasattr(content, 'annotations') and content.annotations:
                            for annotation in content.annotations:
                                if annotation.type == "container_file_citation":
                                    local_path = self._save_yandex_file(
                                        annotation.file_id,
                                        annotation.filename
                                    )
                                    if not local_path.startswith("ERROR"):
                                        downloaded_files.append((annotation.filename, local_path))
            
            # Добавляем информацию о скачанных файлах
            if downloaded_files:
                result_parts.append("\n\n**📎 Скачанные файлы:**")
                for filename, local_path in downloaded_files:
                    result_parts.append(f"- `{filename}` → `{local_path}`")
            
            return "\n\n".join(result_parts) if result_parts else "✅ Код выполнен (без вывода)"
        
        except Exception as e:
            return f"❌ Ошибка выполнения: {str(e)}"
    
    @tool
    def generate_image(
        self,
        prompt: Annotated[str, "Текстовое описание изображения для генерации"],
        size: Annotated[str, "Размер изображения: '1024x1024', '1536x1024' или '1024x1536'"]
    ) -> str:
        """
        Генерирует изображение по текстовому описанию.
        АВТОМАТИЧЕСКИ сохраняет файл в папку output/ и возвращает Markdown-ссылку.
        """
        try:
            response = self.client.responses.create(
                model=f"gpt://{os.getenv('YANDEX_FOLDER_ID')}/{os.getenv('YANDEX_MODEL', 'yandexgpt/latest')}",
                input=prompt,
                tools=[{"type": "image_generation", "size": size}]
            )
            
            for item in response.output:
                if item.type == "image_generation_call" and item.status == "completed":
                    # Автоматически скачиваем и сохраняем
                    local_path = self._save_yandex_file(item.file_id, "generated_image.png")
                    
                    if local_path.startswith("ERROR"):
                        return (
                            f"⚠️ Изображение сгенерировано (File ID: {item.file_id}), "
                            f"но не удалось сохранить: {local_path}"
                        )
                    
                    # Возвращаем готовый Markdown для агента
                    return (
                        f"✅ Изображение сгенерировано и сохранено.\n\n"
                        f"![{prompt[:50]}]({local_path})\n\n"
                        f"**Локальный путь:** `{local_path}`\n"
                        f"**File ID (для справки):** `{item.file_id}`"
                    )
            
            return "❌ Изображение не было сгенерировано"
        
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
        """Подключает MCP-сервер для расширения возможностей агента через внешний API."""
        try:
            mcp_config = {
                "type": "mcp",
                "server_url": server_url,
                "server_label": server_label,
                "description": description,
                "require_approval": require_approval
            }
            
            return (
                f"✅ Конфигурация MCP-сервера создана:\n"
                f"{json.dumps(mcp_config, indent=2, ensure_ascii=False)}\n\n"
                f"Добавьте эту конфигурацию в tools при следующем вызове API"
            )
        
        except Exception as e:
            return f"❌ Ошибка создания конфигурации: {str(e)}"

    @tool
    def web_search(
        self,
        query: Annotated[str, "Поисковый запрос, например 'сервисы генерации презентаций ИИ конкуренты'"],
        allowed_domains: Annotated[list, "До 5 доменов для ограничения поиска (необязательно)"] = None,
        search_context_size: Annotated[str, "Полнота контекста поиска: 'low', 'medium' или 'high'"] = "medium"
    ) -> str:
        """Ищет актуальную информацию в интернете через встроенный web_search
        Яндекс AI Studio. Возвращает факты и список источников (url_citation)."""
        try:
            tool_config = {
                "type": "web_search",
                "search_context_size": search_context_size
            }
            if allowed_domains:
                tool_config["filters"] = {"allowed_domains": allowed_domains[:5]}
            
            response = self.client.responses.create(
                model=f"gpt://{os.getenv('YANDEX_FOLDER_ID')}/{os.getenv('YANDEX_MODEL', 'yandexgpt/latest')}",
                input=query,
                tools=[tool_config],
                temperature=0.3
            )
            
            result_parts = []
            sources = []
            
            for item in response.output:
                if item.type == "message":
                    for content in item.content:
                        if content.type == "output_text":
                            result_parts.append(content.text)
                            # Собираем источники из аннотаций
                            if hasattr(content, 'annotations') and content.annotations:
                                for ann in content.annotations:
                                    if ann.type == "url_citation" and ann.url not in sources:
                                        sources.append(ann.url)
            
            if sources:
                result_parts.append("\n\n**Источники:**")
                for url in sources:
                    result_parts.append(f"- {url}")
            
            cleaned = "\n".join(result_parts) if result_parts else "❌ Поиск не дал результатов"
            # Убираем 3+ подряд идущих переноса строки, оставляя максимум 2
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
            return cleaned
        
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"



# ============================================================
# 4. Фабрика для создания всех инструментов
# ============================================================

def create_all_tools(client=None):
    """Создаёт список всех инструментов для агента."""
    basic_tools = [load_skill, bash_execute, file_read, file_write]
    
    if client:
        yandex_tools = YandexTools(client)
        advanced_tools = [
            yandex_tools.upload_file,
            yandex_tools.download_file,
            yandex_tools.list_files,
            yandex_tools.execute_code,
            yandex_tools.generate_image,
            yandex_tools.use_mcp_server,
            yandex_tools.web_search        
        ]
        return basic_tools + advanced_tools
    
    return basic_tools

