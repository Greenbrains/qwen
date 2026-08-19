"""
📋 agent_tools.py — фабрика инструментов.
Version: 5.2.0
Description: Декоратор @tool, локальные инструменты, YandexTools (с folder_id для model_uri).
"""
import inspect
import json
import logging
import re
import subprocess
import time as _time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Annotated, get_args, get_origin, get_type_hints


logger = logging.getLogger("agent.tools")


def _short_args(args: dict, max_total: int = 60) -> str:
    if not args:
        return ""
    parts = []
    for k, v in args.items():
        sv = str(v)
        if len(sv) > 30:
            sv = sv[:27] + "..."
        parts.append(f"{k}={sv!r}")
    s = ", ".join(parts)
    return s if len(s) <= max_total else s[: max_total - 3] + "..."


def tool(func=None, *, name: str = None, description: str = None):
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
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        for obj in (fn, wrapper):
            obj._tool_schema = tool_schema
            obj._tool_name = tool_name
            obj._tool_description = tool_description
        return wrapper
    return decorator(func) if func is not None else decorator


def _extract_parameters_schema(fn) -> dict:
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
            actual_type = param_type.__args__[0]
            if param_type.__metadata__:
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
    origin = get_origin(python_type)
    if origin is not None:
        args = get_args(python_type)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _python_type_to_json(non_none[0])
    type_map = {
        str: "string", int: "integer", float: "number",
        bool: "boolean", list: "array", dict: "object",
    }
    return type_map.get(python_type, "string")


def collect_tools(*tool_functions) -> list:
    return [fn._tool_schema for fn in tool_functions if hasattr(fn, "_tool_schema")]


def create_tool_router(*tool_functions) -> dict:
    return {fn._tool_name: fn for fn in tool_functions if hasattr(fn, "_tool_name")}


# ============================================================
# Скиллы
# ============================================================
SKILLS_ROOT = Path(".agents/skills")
SKILLS_CATALOG_FILE = SKILLS_ROOT / "SKILL.md"


def load_skills_catalog() -> str:
    if SKILLS_CATALOG_FILE.exists():
        return SKILLS_CATALOG_FILE.read_text(encoding="utf-8")
    if SKILLS_ROOT.exists():
        names = sorted(p.name for p in SKILLS_ROOT.iterdir() if p.is_dir())
        if names:
            return "Обнаружены навыки (без описаний):\n" + "\n".join(f"- {n}" for n in names)
    return "Каталог навыков пуст."


@tool
def load_skill(
    skill_name: Annotated[str, "Имя навыка из каталога, напр. 'touragent'. Пусто — вернуть каталог всех навыков."] = "",
) -> str:
    """Загружает инструкцию навыка из .agents/skills/<name>/<name>.md."""
    if not skill_name:
        return load_skills_catalog()
    skill_path = SKILLS_ROOT / skill_name / f"{skill_name}.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return f"❌ Навык '{skill_name}' не найден. Вызови load_skill() без аргумента для списка."


# ============================================================
# Локальные инструменты
# ============================================================
@tool
def bash_execute(command: Annotated[str, "Bash-команда для локального выполнения."]) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return result.stdout or "✅ Выполнено успешно (без вывода)"
        return f"❌ Ошибка (код {result.returncode}):\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "❌ Превышено время выполнения (60 секунд)"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"


@tool
def file_read(file_path: Annotated[str, "Путь к локальному файлу для чтения."]) -> str:
    path = Path(file_path)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"❌ Файл не найден: {file_path}"


@tool
def file_write(
    file_path: Annotated[str, "Путь к локальному файлу для записи."],
    content: Annotated[str, "Содержимое для записи в файл."],
) -> str:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"✅ Файл сохранён: {file_path}"


# ============================================================
# YandexTools — с folder_id для правильного model_uri
# ============================================================
class YandexTools:
    """Инструменты Яндекс AI Studio.
    
    ВАЖНО: принимает folder_id, чтобы формировать полный URI
    gpt://{folder_id}/{model_name} — обязательный формат для API Яндекса.
    """

    def __init__(self, client, folder_id: str, model_name: str = "qwen3.6-35b-a3b/latest"):
        self.client = client
        self.folder_id = folder_id
        self.model_name = model_name
        # КЛЮЧЕВОЕ: полный URI для всех вызовов API
        self.model_uri = f"gpt://{folder_id}/{model_name}"
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def _save_yandex_file(self, file_id: str, suggested_name: str = None) -> str:
        try:
            file_content = self.client.files.content(file_id)
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
    def upload_file(
        self,
        local_path: Annotated[str, "Путь к локальному файлу"],
        purpose: Annotated[str, "'user_data' для Code Interpreter"],
    ) -> str:
        path = Path(local_path)
        if not path.exists():
            return f"❌ Файл не найден: {local_path}"
        try:
            with open(path, "rb") as f:
                uploaded = self.client.files.create(file=f, purpose=purpose)
            return f"✅ Файл загружен:\n- Имя: {path.name}\n- File ID: {uploaded.id}"
        except Exception as e:
            return f"❌ Ошибка загрузки: {str(e)}"

    @tool
    def download_file(
        self,
        file_id: Annotated[str, "Идентификатор файла в Files API"],
        local_path: Annotated[str, "Локальный путь для сохранения"],
    ) -> str:
        try:
            file_content = self.client.files.content(file_id)
            path = Path(local_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(file_content.read())
            return f"✅ Файл скачан: {local_path}"
        except Exception as e:
            return f"❌ Ошибка скачивания: {str(e)}"

    @tool
    def list_files(self) -> str:
        try:
            files = self.client.files.list()
            if not files.data:
                return "📭 Список файлов пуст"
            result = "📋 Загруженные файлы:\n"
            for file in files.data:
                result += f"- {file.filename} (ID: {file.id}, {file.bytes} bytes)\n"
            return result
        except Exception as e:
            return f"❌ Ошибка получения списка: {str(e)}"

    @tool
    def execute_code(
        self,
        code: Annotated[str, "Python-код для выполнения"],
        file_ids: Annotated[list, "Список file_id"] = None,
    ) -> str:
        """Выполняет Python-код через Code Interpreter (streaming + polling)."""
        try:
            container_config = {"type": "auto"}
            if file_ids:
                container_config["file_ids"] = file_ids

            stream = self.client.responses.create(
                model=self.model_uri,  # ← ПОЛНЫЙ URI
                instructions=(
                    "Ты Python-программист. Выполни код. "
                    "Файлы сохраняй с простым именем ('presentation.pptx'), без пути."
                ),
                input=code,
                tools=[{"type": "code_interpreter", "container": container_config}],
                stream=True,
            )

            resp_id = None
            for event in stream:
                if getattr(event, "type", None) == "response.in_progress":
                    resp_id = event.response.id
                    break
            if not resp_id:
                return "❌ Code Interpreter: не получен response ID"

            logger.info(f"Code Interpreter: task={resp_id}, polling...")

            max_wait = 180
            waited = 0
            response = None
            while waited < max_wait:
                response = self.client.responses.retrieve(resp_id)
                status = getattr(response, "status", None)
                if status in ("completed", "failed", "cancelled"):
                    break
                _time.sleep(2)
                waited += 2

            if response is None or getattr(response, "status", None) != "completed":
                return f"❌ Code Interpreter status: {getattr(response, 'status', 'unknown')}"

            result_parts, downloaded = [], []
            for item in response.output:
                if getattr(item, "type", None) == "code_interpreter_call":
                    result_parts.append(f"```python\n{getattr(item, 'code', '')}\n```")
                    for out in getattr(item, "outputs", []) or []:
                        if getattr(out, "logs", ""):
                            result_parts.append(f"**Вывод:**\n```\n{out.logs.strip()}\n```")
                elif getattr(item, "type", None) == "message":
                    for content in getattr(item, "content", []) or []:
                        if getattr(content, "type", None) == "output_text":
                            result_parts.append(getattr(content, "text", ""))
                        for ann in getattr(content, "annotations", None) or []:
                            if getattr(ann, "type", None) == "container_file_citation":
                                fid = getattr(ann, "file_id", None)
                                fn = getattr(ann, "filename", None)
                                if fid:
                                    lp = self._save_yandex_file(fid, fn)
                                    if not lp.startswith("ERROR"):
                                        downloaded.append((fn or fid, lp))

            if downloaded:
                result_parts.append("\n\n**📎 Скачанные файлы в output/:**")
                for fn, lp in downloaded:
                    result_parts.append(f"- `{fn}` → `{lp}`")
            else:
                result_parts.append("\n\n_ℹ️ Файлы не созданы._")

            return "\n\n".join(result_parts) if result_parts else "✅ Код выполнен"
        except Exception as e:
            logger.exception("execute_code failed")
            return f"❌ Ошибка выполнения: {str(e)}"

    @tool
    def generate_image(
        self,
        prompt: Annotated[str, "Текстовое описание"],
        size: Annotated[str, "Размер: '1024x1024'"],
    ) -> str:
        try:
            response = self.client.responses.create(
                model=self.model_uri,  # ← ПОЛНЫЙ URI
                input=prompt,
                tools=[{"type": "image_generation", "size": size}],
            )
            for item in response.output:
                if getattr(item, "type", None) == "image_generation_call":
                    lp = self._save_yandex_file(getattr(item, "result"), "image.png")
                    return f"✅ Изображение: `{lp}`"
            return "❌ Не сгенерировано"
        except Exception as e:
            return f"❌ Ошибка: {str(e)}"

    @tool
    def web_search(
        self,
        query: Annotated[str, "Поисковый запрос"],
        allowed_domains: Annotated[list, "До 5 доменов"] = None,
        search_context_size: Annotated[str, "'low', 'medium' или 'high'"] = "medium",
    ) -> str:
        try:
            tool_config = {"type": "web_search", "search_context_size": search_context_size}
            if allowed_domains:
                tool_config["filters"] = {"allowed_domains": allowed_domains[:5]}
            response = self.client.responses.create(
                model=self.model_uri,  # ← ПОЛНЫЙ URI
                input=query,
                tools=[tool_config],
                temperature=0.3,
            )
            result_parts, sources = [], []
            for item in response.output:
                if getattr(item, "type", None) == "message":
                    for content in getattr(item, "content", []) or []:
                        if getattr(content, "type", None) == "output_text":
                            result_parts.append(getattr(content, "text", ""))
                        for ann in getattr(content, "annotations", None) or []:
                            if getattr(ann, "type", None) == "url_citation":
                                url = getattr(ann, "url", None)
                                if url and url not in sources:
                                    sources.append(url)
            if sources:
                result_parts.append("\n\n**Источники:**")
                result_parts += [f"- {u}" for u in sources]
            cleaned = "\n".join(result_parts) if result_parts else "❌ Поиск не дал результатов"
            return re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        except Exception as e:
            return f"❌ Ошибка поиска: {str(e)}"


# ============================================================
# Реестр «навык → инструменты»
# ============================================================
SKILL_TOOLSETS = {
    "touragent": ["load_skill", "tutu_call", "file_write", "file_read"],
    "marketingskills": [
        "load_skill", "web_search", "execute_code",
        "upload_file", "download_file", "list_files",
        "file_read", "file_write", "generate_image",
    ],
    "general": [
        "load_skill", "bash_execute", "file_read", "file_write",
        "web_search", "execute_code", "generate_image",
        "upload_file", "download_file", "list_files",
    ],
}


def filter_tools_for_skill(all_tool_funcs, skill_name: str):
    allowed = SKILL_TOOLSETS.get(skill_name)
    if not allowed:
        return list(all_tool_funcs)
    allowed_set = set(allowed)
    return [fn for fn in all_tool_funcs if getattr(fn, "_tool_name", None) in allowed_set]