import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from tools import create_all_tools, collect_tools, create_tool_router, load_skills_catalog

load_dotenv()

# ============================================================
# Конфигурация Яндекс AI Studio
# ============================================================

YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
YANDEX_MODEL = os.getenv("YANDEX_MODEL", "yandexgpt/latest")

# Клиент OpenAI для работы с Яндекс AI Studio (совместимый API)
client = OpenAI(
    api_key=YANDEX_API_KEY,
    base_url="https://ai.api.cloud.yandex.net/v1",
    project=YANDEX_FOLDER_ID,
)

# Инструменты
ALL_TOOLS = create_all_tools(client)
TOOLS_SCHEMA = collect_tools(*ALL_TOOLS)
TOOL_ROUTER = create_tool_router(*ALL_TOOLS)

# ============================================================
# Системный промпт
# ------------------------------------------------------------
# ВАЖНО: промпт НЕ содержит подсказок под конкретные задачи
# (никаких имён навыков, номеров разделов, имён файлов, рецептов
# зависимостей). Всё предметное знание живёт в навыках (.md) и в
# docstring'ах инструментов. Задача промпта — научить агента ОБЩЕЙ
# дисциплине: как выбирать навык и как ему следовать.
# ============================================================

SYSTEM_PROMPT_BASE = """Ты — агент-исполнитель с доступом к Яндекс AI Studio и набору инструментов.

## Базовые возможности
- **Навыки (Skills)** — переиспользуемые инструкции. Каталог доступных навыков приведён ниже. Загружай нужный навык через `load_skill` и следуй ему.
- **Локальное выполнение** — bash-команды, чтение и запись файлов.
- **Code Interpreter** (`execute_code`) — выполнение Python в изолированном контейнере; артефакты автоматически скачиваются в папку `output/`.
- **Files API** — загрузка и скачивание файлов в облачное хранилище.
- **Web Search** (`web_search`) — актуальные данные из интернета с источниками.
- **Image Generation** (`generate_image`) — генерация изображений (сохраняются в `output/`).
- **MCP Servers** — подключение внешних сервисов.

## Как работать с навыками (главное правило)
1. Прочитай каталог навыков ниже и определи, покрывает ли какой-то навык запрос пользователя (по колонке «когда использовать»).
2. Если да — вызови `load_skill(skill_name=...)` и ДАЛЬШЕ действуй строго по загруженному тексту навыка: следуй его рабочему процессу, шагам и разделам буквально, не додумывая деталей за навык.
3. Если навык ссылается на конкретные разделы, файлы, форматы вывода или ограничения — соблюдай их точно так, как написано в навыке.
4. Если подходящего навыка нет — работай общими инструментами.
5. Не выбирай навык «по памяти» и не угадывай имя — бери его из каталога. Если сомневаешься между навыками, вызови `load_skill()` без аргумента, чтобы перечитать каталог.

## Папка output/
Артефакты (файлы, изображения, отчёты) сохраняются в `output/`. Когда инструмент возвращает путь вида `output/<имя>`, используй в ответе именно этот путь из результата инструмента — не выдумывай имена файлов и не подставляй заглушки-ссылки.

## Общая дисциплина
- Перед действием сообщай пользователю, что делаешь.
- Сложную задачу разбивай на шаги.
- НИКОГДА не выводи в чат секретные ключи и токены.
- Спрашивай подтверждение перед деструктивными операциями (удаление, перезапись).
- Опирайся на фактические результаты инструментов, а не на предположения.
"""


def build_system_prompt() -> str:
    """Собирает системный промпт: общая дисциплина + актуальный каталог навыков.

    Каталог подгружается из файла на диске, поэтому добавление/изменение
    навыков не требует правок в коде агента и не тянет за собой подсказок
    под конкретную задачу.
    """
    catalog = load_skills_catalog()
    return (
        SYSTEM_PROMPT_BASE
        + "\n\n## Каталог доступных навыков\n"
        + "(Выбери подходящий по колонке «когда использовать» и загрузи через load_skill.)\n\n"
        + catalog
    )


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
            "content": build_system_prompt(),
        })

    conversation_history.append({
        "role": "user",
        "content": user_message,
    })

    print("🤖 Агент думает...\n")

    max_iterations = 10

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=f"gpt://{YANDEX_FOLDER_ID}/{YANDEX_MODEL}",
            messages=conversation_history,
            tools=TOOLS_SCHEMA if TOOLS_SCHEMA else None,
            tool_choice="auto" if TOOLS_SCHEMA else None,
            temperature=0.3,
            max_tokens=2000,
        )

        message = response.choices[0].message

        # Модель не хочет вызывать инструменты — возвращаем финальный ответ
        if not message.tool_calls:
            conversation_history.append({
                "role": "assistant",
                "content": message.content,
            })
            return message.content, conversation_history

        # Ответ модели с tool_calls
        conversation_history.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [tc.model_dump() for tc in message.tool_calls],
        })

        # Выполняем каждый вызов инструмента
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                func_args = {}

            print(f"🔧 Вызов инструмента: {func_name}({func_args})")

            if func_name in TOOL_ROUTER:
                try:
                    fn = TOOL_ROUTER[func_name]
                    if 'client' in fn.__code__.co_varnames:
                        result = fn(client=client, **func_args)
                    else:
                        result = fn(**func_args)
                    result_text = str(result)
                except Exception as e:
                    result_text = f"❌ Ошибка выполнения: {str(e)}"
            else:
                result_text = f"❌ Инструмент '{func_name}' не найден"

            print(f"   → Результат: {result_text[:100]}...\n")

            conversation_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_text,
            })

    return "❌ Превышено максимальное количество итераций", conversation_history


# ============================================================
# Интерактивный режим
# ============================================================

def interactive_mode():
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
# Примеры использования (демо инструментов, без предметных подсказок)
# ============================================================

def example_code_interpreter():
    print("\n" + "=" * 60)
    print("📊 Пример: Code Interpreter")
    print("=" * 60)

    response, _ = chat_with_agent(
        "Построй график sin(x) на отрезке [0, 10] и сохрани его в PNG.",
        [],
    )
    print(f"\nРезультат:\n{response}\n")


def example_file_upload():
    print("\n" + "=" * 60)
    print("📁 Пример: Загрузка файла")
    print("=" * 60)

    test_file = Path("test_data.csv")
    test_file.write_text("name,value\nitem1,100\nitem2,200\nitem3,300")

    response, _ = chat_with_agent(
        "Загрузи файл test_data.csv в Files API с назначением user_data.",
        [],
    )
    print(f"\nРезультат:\n{response}\n")


def example_image_generation():
    print("\n" + "=" * 60)
    print("🎨 Пример: Генерация изображения")
    print("=" * 60)

    response, _ = chat_with_agent(
        "Сгенерируй изображение серого кота, обнимающего выдру, размер 1024x1024.",
        [],
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
