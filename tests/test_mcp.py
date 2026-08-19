"""
test_mcp.py — Ручной просмотр того, что получает агент с MCP-сервера.
Запуск: python test_mcp.py

Суть tutu_tools.py в трёх предложениях
_make_proxy_tool берёт все 16 инструментов и оборачивает их в один tutu_call(tool, args_json). LLM видит одну функцию с enum из 16 имён, а не 16 отдельных схем.
tutu_catalog_markdown генерирует компактную таблицу (имя + описание + список полей), которая вставляется в системный промпт — чтобы модель знала, какие поля у каждого инструмента.
При вызове tutu_call прокси до отправки на сервер валидирует аргументы (_validate_args) и приводит типы (_coerce_types), экономя один round-trip если модель ошиблась.
"""
"""
test_mcp.py — ручной просмотр того, что получает агент с MCP-сервера.
Весь вывод сохраняется в mcp_test_out.md (в корне проекта),
в консоль идут только короткие статус-сообщения.

Запускать можно откуда угодно:
    python tests/test_mcp.py   (из корня)
    python test_mcp.py         (из папки tests/)
"""
import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path

# .../tests/test_mcp.py -> parent.parent = корень проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.core.mcp.sync_client import SyncMCPClient
from agent.core.mcp.tutu_tools import (
    _make_proxy_tool,
    _schema_index,
    tutu_catalog_markdown,
)
from agent.core.prompts.loader import PromptLoader

SEP = "=" * 70
OUT_FILE = PROJECT_ROOT / "mcp_test_out.md"


def console(msg: str):
    """Короткие статусы в терминал (stderr), не попадают в файл."""
    print(msg, file=sys.stderr)


def run_checks():
    """Всё содержимое уйдёт в файл (stdout перенаправлен)."""

    print(f"# Вывод test_mcp.py — сгенерировано {datetime.now():%Y-%m-%d %H:%M:%S}\n")

    # ── 1. Подключение к MCP-серверу ─────────────────────────────────
    print(SEP)
    print("1. ПОДКЛЮЧЕНИЕ К MCP-СЕРВЕРУ")
    print(SEP)

    client = SyncMCPClient(url="https://mcp.tutu.ru/mcp")
    if not client.initialize():
        print("❌ Не удалось подключиться к серверу.")
        return
    print(f"✅ Подключено. Session ID: {client.session_id}\n")
    console("✅ Подключено к MCP-серверу")

    # ── 2. СЫРОЙ список инструментов ─────────────────────────────────
    print(SEP)
    print("2. СЫРОЙ list_tools() — что отдаёт сервер")
    print(SEP)

    tools_raw = client.list_tools(force=True)
    print(f"Всего инструментов: {len(tools_raw)}\n")

    for i, t in enumerate(tools_raw, 1):
        name = t.get("name", "?")
        desc = (t.get("description") or "").strip()
        schema = t.get("inputSchema") or {}
        props = schema.get("properties", {})
        required = schema.get("required", [])

        print(f"  [{i:02d}] {name}")
        print(f"       Описание: {desc[:120]}")
        print(f"       Поля:     {list(props.keys())}")
        print(f"       Required: {required}")
        print()
    console("✍️  Раздел 2: сырой list_tools записан")

    # ── 3. Полные inputSchema ────────────────────────────────────────
    print(SEP)
    print("3. ПОЛНЫЕ inputSchema каждого инструмента")
    print(SEP)

    schema_idx = _schema_index(client)
    for name, schema in schema_idx.items():
        print(f"\n  ┌─ {name}")
        print(f"  │  {json.dumps(schema, ensure_ascii=False, indent=2)}")
        print(f"  └{'─' * 50}")
    console("✍️  Раздел 3: inputSchema записаны")

    # ── 4. Каталог для системного промпта ────────────────────────────
    print(f"\n{SEP}")
    print("4. КАТАЛОГ ДЛЯ ПРОМПТА (tutu_catalog_markdown)")
    print(SEP)

    catalog_md = tutu_catalog_markdown(client)
    print(catalog_md)
    console("✍️  Раздел 4: каталог записан")

    # ── 5. Прокси-инструмент tutu_call ───────────────────────────────
    print(f"\n{SEP}")
    print("5. ПРОКСИ-ИНСТРУМЕНТ tutu_call — схема, которую видит LLM")
    print(SEP)

    proxy_fn = _make_proxy_tool(client)
    print(f"  Имя:        {proxy_fn._tool_name}")
    print(f"  Описание:   {proxy_fn._tool_description}")
    print(f"\n  JSON Schema для LLM:")
    print(json.dumps(proxy_fn._tool_schema, ensure_ascii=False, indent=2))
    console("✍️  Раздел 5: схема tutu_call записана")

    # ── 6. Итоговый системный промпт ─────────────────────────────────
    print(f"\n{SEP}")
    print("6. ИТОГОВЫЙ СИСТЕМНЫЙ ПРОМПТ (loader + каталог MCP)")
    print(SEP)

    prompts_dir = PROJECT_ROOT / ".agents" / "prompts"
    if (prompts_dir / "system.yaml").exists():
        loader = PromptLoader(prompts_dir=prompts_dir)
        print(loader.render_system_prompt(mcp_catalog_markdown=catalog_md))
    else:
        print(f"⚠️  {prompts_dir / 'system.yaml'} не найден — показываю только каталог.")
        print(catalog_md)
    console("✍️  Раздел 6: системный промпт записан")

    # ── 7. Размеры ───────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("7. РАЗМЕРЫ (примерная оценка токенов)")
    print(SEP)

    raw_json_str = json.dumps(tools_raw, ensure_ascii=False)
    proxy_schema_str = json.dumps(proxy_fn._tool_schema, ensure_ascii=False)
    print(f"  Сырой list_tools JSON:      {len(raw_json_str):>6} симв ≈ {len(raw_json_str) // 4:>5} токенов")
    print(f"  Каталог (markdown-таблица): {len(catalog_md):>6} симв ≈ {len(catalog_md) // 4:>5} токенов")
    print(f"  Схема tutu_call:            {len(proxy_schema_str):>6} симв ≈ {len(proxy_schema_str) // 4:>5} токенов")
    print()
    print("  💡 Агент видит ТОЛЬКО tutu_call (одна схема) + каталог в промпте.")


console(f"📝 Полный вывод будет сохранён в: {OUT_FILE}")
with open(OUT_FILE, "w", encoding="utf-8") as f:
    with contextlib.redirect_stdout(f):
        run_checks()
console(f"✅ Готово. Открой {OUT_FILE.name} в редакторе.")
