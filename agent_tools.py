"""
📋 agent_tools.py — фабрика инструментов (Async v2.3)
Содержит декоратор @tool, локальные и Yandex-инструменты, реестр скиллов.
"""
import asyncio
import inspect
import json
import logging
import re
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Annotated, get_args, get_origin, get_type_hints

logger = logging.getLogger("agent.tools")

# ============================================================
# Утилиты форматирования
# ============================================================
def _short_args(args: dict, max_total: int = 60) -> str:
    """Formats dictionary arguments into a compact string for logging."""
    if not args: 
        return ""
    parts = [f"{k}={str(v)[:27]+'...' if len(str(v))>30 else str(v)!r}" for k, v in args.items()]
    s = ", ".join(parts)
    return s if len(s) <= max_total else s[: max_total - 3] + "..."

def _short_text(text: str, limit: int = 120) -> str:
    """Truncates text to a single line with a specified character limit."""
    if not text: 
        return ""
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else one_line[:limit] + "…"

# ============================================================
# 1. Декоратор @tool + генерация схем
# ============================================================
def tool(func=None, *, name: str = None, description: str = None):
    """
    Description: Decorator to register a function as an LLM-callable tool and generate its JSON schema.
    Input data:
        - func: The target function.
        - name (str): Optional override for the tool name.
        - description (str): Optional override for the tool description.
    Output: Callable: The wrapped function with attached _tool_schema, _tool_name, and _tool_description.
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
                "parameters": parameters_schema,
            },
        }
        
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            return await fn(*args, **kwargs)
            
        for obj in (fn, wrapper):
            obj._tool_schema = tool_schema
            obj._tool_name = tool_name
            obj._tool_description = tool_description
        return wrapper
        
    return decorator(func) if func is not None else decorator

def _extract_parameters_schema(fn) -> dict:
    """
    Description: Extracts JSON schema from function signature and type hints.
    Input data: fn (Callable): The target function.
    Output: dict: JSON schema dictionary for the function parameters.
    """
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn, include_extras=True)
    except Exception:
        hints = {}
        
    properties, required = {}, []
    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls", "client"):
            continue
            
        param_type = hints.get(param_name, str)
        param_description = ""
        actual_type = param_type
        
        if hasattr(param_type, "__metadata__"):
            actual_type = get_args(param_type)[0]
            if getattr(param_type, "__metadata__", None):
                param_description = param_type.__metadata__[0]
                
        prop_schema = {"type": _python_type_to_json(actual_type)}
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
    """Maps Python type hints to JSON schema types."""
    origin = get_origin(python_type)
    if origin is not None:
        args = get_args(python_type)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _python_type_to_json(non_none[0])
            
    type_map = {str: "string", int: "integer", float: "number", bool: "boolean", list: "array", dict: "object"}
    return type_map.get(python_type, "string")

def collect_tools(*tool_functions) -> list:
    """Extracts tool schemas from a list of decorated functions."""
    return [fn._tool_schema for fn in tool_functions if hasattr(fn, "_tool_schema")]

def create_tool_router(*tool_functions) -> dict:
    """Creates a name-to-function mapping for tool execution."""
    return {fn._tool_name: fn for fn in tool_functions if hasattr(fn, "_tool_name")}

# ============================================================
# 2. Скиллы (навыки)
# ============================================================
SKILLS_ROOT = Path(".agents/skills")
SKILLS_CATALOG_FILE = SKILLS_ROOT / "SKILL.md"

def load_skills_catalog() -> str:
    """
    Description: Reads the main skills catalog file or lists available skill directories.
    Input data: None.
    Output: str: The catalog content or a formatted list of skill names.
    """
    if SKILLS_CATALOG_FILE.exists():
        return SKILLS_CATALOG_FILE.read_text(encoding="utf-8")
    if SKILLS_ROOT.exists():
        names = sorted(p.name for p in SKILLS_ROOT.iterdir() if p.is_dir())
        if names:
            return "Обнаружены навыки (без описаний):\n" + "\n".join(f"- {n}" for n in names)
    return "Каталог навыков пуст."

@tool
async def load_skill(
    skill_name: Annotated[str, "Имя навыка из каталога, напр. 'touragent'. Пусто — вернуть каталог всех навыков."] = ""
) -> str:
    """
    Description: Loads a specific skill instruction file or returns the full catalog.
    Input data:
        - skill_name (str): The name of the skill to load. Empty string returns the catalog.
    Output: str: The markdown content of the skill or the catalog text.
    """
    if not skill_name:
        return load_skills_catalog()
    skill_path = SKILLS_ROOT / skill_name / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return f"❌ Навык '{skill_name}' не найден. Вызови load_skill() без аргумента для списка."

# ============================================================
# 3. Локальные инструменты (Async)
# ============================================================
@tool
async def bash_execute(command: Annotated[str, "Bash-команда для локального выполнения."]) -> str:
    """
    Description: Executes a bash command locally and returns stdout/stderr.
    Input data:
        - command (str): The shell command to execute.
    Output: str: The command output or an error message.
    """
    try:
        process = await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
        if process.returncode == 0:
            return stdout.decode('utf-8').strip() or "✅ Выполнено успешно (без вывода)"
        return f"❌ Ошибка (код {process.returncode}):\n{stderr.decode('utf-8')}"
    except asyncio.TimeoutError:
        return "❌ Превышено время выполнения (60 секунд)"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"

@tool
async def file_read(file_path: Annotated[str, "Путь к локальному файлу для чтения."]) -> str:
    """
    Description: Reads the content of a local file.
    Input data:
        - file_path (str): The path to the file.
    Output: str: The file content or an error message.
    """
    path = Path(file_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"❌ Файл не найден: {file_path}"

@tool
async def file_write(
    file_path: Annotated[str, "Путь к локальному файлу для записи."],
    content: Annotated[str, "Содержимое для записи в файл."],
) -> str:
    """
    Description: Writes content to a local file, creating directories if necessary.
    Input data:
        - file_path (str): The target file path.
        - content (str): The text content to write.
    Output: str: Confirmation message or error.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"✅ Файл сохранён: {file_path}"

# ============================================================
# 4. Инструменты Яндекс AI Studio (Async)
# ============================================================
class YandexTools:
    """Tools requiring an AsyncOpenAI client connected to Yandex AI Studio."""
    def __init__(self, client, model_name: str):
        self.client = client
        self.model_name = model_name
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    async def _save_yandex_file(self, file_id: str, suggested_name: str = None) -> str:
        """Helper to download and save a file from Yandex Files API."""
        try:
            file_content = await self.client.files.content(file_id)
            if suggested_name:
                safe = Path(suggested_name).name
                filename = f"{Path(safe).stem}_{file_id[:8]}{Path(safe).suffix}"
            else:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"file_{ts}_{file_id[:8]}"
            local_path = self.output_dir / filename
            with open(local_path, "wb") as f:
                f.write(file_content.read())
            return str(local_path).replace("\\", "/")
        except Exception as e:
            return f"ERROR: {e}"

    @tool
    async def upload_file(
        self,
        local_path: Annotated[str, "Путь к локальному файлу для загрузки в Яндекс AI Studio"],
        purpose: Annotated[str, "'user_data' для Code Interpreter, 'assistants' для Vector Store"],
    ) -> str:
        """
        Description: Uploads a local file to Yandex AI Studio Files API.
        Input data:
            - local_path (str): Path to the local file.
            - purpose (str): The intended use of the file.
        Output: str: Upload confirmation with File ID and size.
        """
        path = Path(local_path)
        if not path.exists():
            return f"❌ Файл не найден: {local_path}"
        try:
            with open(path, "rb") as f:
                uploaded = await self.client.files.create(file=f, purpose=purpose)
            return f"✅ Файл загружен:\n- Имя: {path.name}\n- File ID: {uploaded.id}\n- Размер: {uploaded.bytes} bytes"
        except Exception as e:
            return f"❌ Ошибка загрузки: {str(e)}"

    @tool
    async def download_file(
        self,
        file_id: Annotated[str, "Идентификатор файла в Files API"],
        local_path: Annotated[str, "Локальный путь для сохранения файла"],
    ) -> str:
        """
        Description: Downloads a file from Yandex AI Studio Files API by file_id.
        Input data:
            - file_id (str): The Yandex file identifier.
            - local_path (str): The destination path on the local filesystem.
        Output: str: Success confirmation or error message.
        """
        try:
            file_content = await self.client.files.content(file_id)
            path = Path(local_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(file_content.read())
            return f"✅ Файл скачан и сохранён: {local_path}"
        except Exception as e:
            return f"❌ Ошибка скачивания: {str(e)}"

    @tool
    async def list_files(self) -> str:
        """
        Description: Retrieves a list of all files uploaded to the Files API.
        Input data: None.
        Output: str: Formatted list of files with names, IDs, and sizes.
        """
        try:
            files = await self.client.files.list()
            if not files.data:
                return "📭 Список файлов пуст"
            result = "📋 Загруженные файлы:\n"
            for file in files.data:
                result += f"- {file.filename} (ID: {file.id}, {file.bytes} bytes)\n"
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"

    @tool
    async def execute_code(
        self,
        code: Annotated[str, "Python-код для выполнения в изолированном контейнере"],
        file_ids: Annotated[list, "Список file_id файлов, нужных для выполнения кода"] = None,
    ) -> str:
        """
        Description: Executes Python code in an isolated Code Interpreter container.
        Input data:
            - code (str): The Python code to execute.
            - file_ids (list): Optional list of file IDs to mount in the container.
        Output: str: The execution output, logs, and paths to any generated files.
        """
        try:
            container_config = {"type": "auto"}
            if file_ids:
                container_config["file_ids"] = file_ids
            response = await self.client.responses.create(
                model=self.model_name,
                instructions="Выполни этот Python-код и верни результат",
                input=code,
                tools=[{"type": "code_interpreter", "container": container_config}],
            )
            result_parts, downloaded = [], []
            for item in response.output:
                if item.type == "code_interpreter_call":
                    result_parts.append(f"```python\n{item.code}\n```")
                    for out in item.outputs:
                        if out.logs:
                            result_parts.append(f"**Вывод:**\n```\n{out.logs}\n```")
                elif item.type == "message":
                    for content in item.content:
                        if content.type == "output_text":
                            result_parts.append(content.text)
                        if getattr(content, "annotations", None):
                            for ann in content.annotations:
                                if ann.type == "container_file_citation":
                                    lp = await self._save_yandex_file(ann.file_id, ann.filename)
                                    if not lp.startswith("ERROR"):
                                        downloaded.append((ann.filename, lp))
            if downloaded:
                result_parts.append("\n\n**📎 Скачанные файлы:**")
                for fn, lp in downloaded:
                    result_parts.append(f"- `{fn}` → `{lp}`")
            return "\n\n".join(result_parts) if result_parts else "✅ Код выполнен (без вывода)"
        except Exception as e:
            return f"❌ Ошибка выполнения: {str(e)}"

    @tool
    async def generate_image(
        self,
        prompt: Annotated[str, "Текстовое описание изображения для генерации"],
        size: Annotated[str, "Размер: '1024x1024', '1536x1024' или '1024x1536'"],
    ) -> str:
        """
        Description: Generates an image based on a text prompt and saves it locally.
        Input data:
            - prompt (str): The text description of the image.
            - size (str): The desired image dimensions.
        Output: str: Confirmation with the local file path and File ID.
        """
        try:
            response = await self.client.responses.create(
                model=self.model_name, input=prompt,
                tools=[{"type": "image_generation", "size": size}],
            )
            for item in response.output:
                if item.type == "image_generation_call":
                    local_path = await self._save_yandex_file(item.result, "image.png")
                    return f"✅ Изображение сгенерировано\n\n**Локальный путь:** `{local_path}`\n**File ID:** `{item.result}`"
            return "❌ Изображение не было сгенерировано"
        except Exception as e:
            return f"❌ Ошибка генерации: {str(e)}"

    @tool
    async def web_search(
        self,
        query: Annotated[str, "Поисковый запрос"],
        allowed_domains: Annotated[list, "До 5 доменов для ограничения поиска"] = None,
        search_context_size: Annotated[str, "Полнота контекста: 'low', 'medium' или 'high'"] = "medium",
    ) -> str:
        """
        Description: Searches the internet for up-to-date information using Yandex's built-in web search.
        Input data:
            - query (str): The search query.
            - allowed_domains (list): Optional list of up to 5 domains to restrict the search.
            - search_context_size (str): Context depth ('low', 'medium', or 'high').
        Output: str: The search results summary and source URLs.
        """
        try:
            tool_config = {"type": "web_search", "search_context_size": search_context_size}
            if allowed_domains:
                tool_config["filters"] = {"allowed_domains": allowed_domains[:5]}
            response = await self.client.responses.create(
                model=self.model_name, input=query, tools=[tool_config], temperature=0.3
            )
            result_parts, sources = [], []
            for item in response.output:
                if item.type == "message":
                    for content in item.content:
                        if content.type == "output_text":
                            result_parts.append(content.text)
                            for ann in getattr(content, "annotations", None) or []:
                                if ann.type == "url_citation" and ann.url not in sources:
                                    sources.append(ann.url)
            if sources:
                result_parts.append("\n\n**Источники:**")
                result_parts += [f"- {u}" for u in sources]
            cleaned = "\n".join(result_parts) if result_parts else "❌ Поиск не дал результатов"
            return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"

# ============================================================
# 5. Реестр «навык → инструменты»
# ============================================================

SKILL_TOOLSETS = {
    "touragent": ["load_skill", "tutu_call", "file_write", "file_read"],
    "marketingskills": [
        "load_skill", "web_search", "execute_code",
        "upload_file", "download_file", "list_files", "file_read", "file_write",
    ],
    # general: лёгкий набор без дорогого MCP — экономия токенов на схемах.
    "general": ["load_skill"],
}

def filter_tools_for_skill(all_tool_funcs, skill_name: str):
    """
    Description: Filters the global tool list to only include those permitted for a specific skill.
    Input data:
        - all_tool_funcs: List of all available tool functions.
        - skill_name (str): The target skill identifier.
    Output: list: A filtered list of tool functions.
    """
    allowed = SKILL_TOOLSETS.get(skill_name)
    if not allowed:
        return list(all_tool_funcs)
    allowed_set = set(allowed)
    return [fn for fn in all_tool_funcs if getattr(fn, "_tool_name", None) in allowed_set]

# ============================================================
# 6. Фабрика инструментов
# ============================================================
def create_all_tools(client=None, model_name: str = "yandexgpt/latest", mcp_client=None, mcp_mode: str = "proxy"):
    """
    Description: Aggregates and returns the complete list of tool functions for an agent.
    Input data:
        - client: The AsyncOpenAI client instance.
        - model_name (str): The target model identifier.
        - mcp_client: The initialized MCP client (optional).
        - mcp_mode (str): The MCP integration mode (e.g., 'proxy').
    Output: list: A combined list of basic, advanced, and MCP tool functions.
    """
    basic_tools = [load_skill, bash_execute, file_read, file_write]
    advanced_tools = []
    
    if client:
        yt = YandexTools(client, model_name)
        advanced_tools = [
            yt.upload_file, yt.download_file, yt.list_files,
            yt.execute_code, yt.generate_image, yt.web_search,
        ]
        
    mcp_tools = []
    if mcp_client:
        try:
            from tools.mcp import build_tutu_tools
            mcp_tools = build_tutu_tools(mcp_client, mode=mcp_mode)
            logger.info(f"✅ Подключено {len(mcp_tools)} MCP-обёрток (режим={mcp_mode})")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось подключить MCP-инструменты: {e}")
            
    return basic_tools + advanced_tools + mcp_tools