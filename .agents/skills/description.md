# Агент с Tool-Calling для выполнения навыков (LangChain 2026)

Да, именно так! Агент читает `SKILL.md`, определяет нужный навык, загружает его содержимое и использует соответствующие инструменты для выполнения задач.

Вот полноценный пример агента:

## 📁 Структура проекта

```
my-agent/
├── .agents/
│   ├── SKILL.md                    # Каталог навыков
│   └── skills/
│       ├── cloudru-vm/
│       │   └── cloudru-vm.md
│       ├── browser-use/
│       │   └── browser-use.md
│       └── marketingskills/
│           └── marketingskills.md
├── agent.py                        # Код агента
├── tools.py                        # Инструменты
├── requirements.txt
└── .env                            # Переменные окружения
```

---

## 📄 `requirements.txt`

```txt
langchain>=0.3.0
langchain-openai>=0.2.0
langgraph>=0.2.0
python-dotenv>=1.0.0
httpx>=0.27.0
```

---

## 🛠 `tools.py` — Инструменты агента

```python
from langchain_core.tools import tool
import subprocess
import os
from pathlib import Path

@tool
def read_skill_catalog() -> str:
    """Читает каталог навыков SKILL.md для определения доступных навыков."""
    skill_path = Path(".agents/SKILL.md")
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return "❌ Файл SKILL.md не найден"

@tool
def load_skill(skill_name: str) -> str:
    """Загружает содержимое конкретного навыка по его имени.
    
    Args:
        skill_name: Имя навыка (например, 'cloudru-vm', 'browser-use')
    """
    skill_path = Path(f".agents/skills/{skill_name}/{skill_name}.md")
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return f"❌ Навык '{skill_name}' не найден"

@tool
def bash_execute(command: str) -> str:
    """Выполняет bash-команду из навыка (CLI-скрипты).
    
    Args:
        command: Команда для выполнения (например, 'python vm.py list')
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        
        if result.returncode == 0:
            return f"✅ Успешно выполнено:\n{output}"
        else:
            return f"❌ Ошибка (код {result.returncode}):\n{error}"
    except subprocess.TimeoutExpired:
        return "❌ Превышено время выполнения (60 секунд)"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"

@tool
def python_execute(code: str) -> str:
    """Выполняет произвольный Python-код (для кастомных решений).
    
    Args:
        code: Python-код для выполнения
    """
    try:
        # Создаём временный файл и выполняем
        temp_file = Path("/tmp/agent_code.py")
        temp_file.write_text(code, encoding="utf-8")
        
        result = subprocess.run(
            ["python", str(temp_file)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout if result.stdout else ""
        error = result.stderr if result.stderr else ""
        
        if result.returncode == 0:
            return f"✅ Код выполнен:\n{output}"
        else:
            return f"❌ Ошибка выполнения:\n{error}"
    except Exception as e:
        return f"❌ Исключение: {str(e)}"

@tool
def file_read(file_path: str) -> str:
    """Читает содержимое файла.
    
    Args:
        file_path: Путь к файлу (например, '.env', 'config.yaml')
    """
    try:
        path = Path(file_path)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return f"❌ Файл не найден: {file_path}"
    except Exception as e:
        return f" Ошибка чтения: {str(e)}"

@tool
def file_write(file_path: str, content: str) -> str:
    """Записывает содержимое в файл.
    
    Args:
        file_path: Путь к файлу
        content: Содержимое для записи
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"✅ Файл сохранён: {file_path}"
    except Exception as e:
        return f"❌ Ошибка записи: {str(e)}"

@tool
def check_env_variables(variables: list[str]) -> dict:
    """Проверяет наличие необходимых переменных окружения.
    
    Args:
        variables: Список имён переменных (например, ['CP_CONSOLE_KEY_ID', 'PROJECT_ID'])
    """
    result = {}
    for var in variables:
        value = os.getenv(var)
        if value:
            result[var] = "✅ Настроена"
        else:
            result[var] = "❌ Отсутствует"
    return result
```

---

## 🤖 `agent.py` — Главный агент

```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from tools import (
    read_skill_catalog,
    load_skill,
    bash_execute,
    python_execute,
    file_read,
    file_write,
    check_env_variables
)

# Загружаем переменные окружения
load_dotenv()

# Инициализация модели (GPT-4o или аналог)
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0,
    max_tokens=4096
)

# Системный промпт агента
SYSTEM_PROMPT = """Ты — агент-исполнитель навыков (Skills Executor Agent).

## Твоя задача
Помогай пользователю выполнять задачи, используя навыки из каталога `.agents/SKILL.md`.

## Рабочий процесс
1. **Прочитай каталог навыков** через инструмент `read_skill_catalog`
2. **Определи нужный навык** на основе запроса пользователя
3. **Загрузи навык** через `load_skill` с именем навыка
4. **Проверь зависимости** (переменные окружения, установленные пакеты)
5. **Выполни команды** из навыка через `bash_execute` или `python_execute`
6. **Сообщи результат** пользователю

## Важные правила
- НЕ загружай все навыки сразу — только тот, который нужен для задачи
- ВСЕГДА проверяй переменные окружения перед выполнением (особенно для cloudru-vm)
- НЕ выводи секретные ключи в чат
- Если навык требует подтверждения деструктивных действий (delete, stop) — спрашивай пользователя
- Если команда завершилась ошибкой — анализируй вывод и предлагай решение

## Доступные инструменты
- `read_skill_catalog` — читать каталог навыков
- `load_skill` — загрузить конкретный навык
- `bash_execute` — выполнять bash-команды
- `python_execute` — выполнять Python-код
- `file_read` / `file_write` — работа с файлами
- `check_env_variables` — проверка переменных окружения

## Примеры использования
- "Создай виртуальную машину в Cloud.ru" → загрузить cloudru-vm → выполнить команды
- "Открой сайт в браузере" → загрузить browser-use → выполнить browser-use open
- "Создай маркетинговый контекст" → загрузить marketingskills → создать документ
"""

# Создаём агента с инструментами
tools = [
    read_skill_catalog,
    load_skill,
    bash_execute,
    python_execute,
    file_read,
    file_write,
    check_env_variables
]

agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT
)

# Функция для взаимодействия с агентом
def chat_with_agent(user_message: str):
    """Отправляет сообщение агенту и возвращает ответ."""
    
    print(f"\n👤 Пользователь: {user_message}")
    print("🤖 Агент думает...\n")
    
    # Вызываем агент
    response = agent.invoke(
        {"messages": [("user", user_message)]}
    )
    
    # Извлекаем финальный ответ
    final_message = response["messages"][-1].content
    
    print(f"🤖 Агент: {final_message}\n")
    return final_message

# Интерактивный режим
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Агент навыков запущен")
    print("=" * 60)
    print("Введите 'exit' для выхода\n")
    
    while True:
        user_input = input(" Вы: ").strip()
        
        if user_input.lower() in ['exit', 'quit', 'выход']:
            print("👋 До свидания!")
            break
        
        if user_input:
            chat_with_agent(user_input)
```

---

## 🧪 Примеры использования

### Пример 1: Создание ВМ в Cloud.ru

```
👤 Вы: Создай виртуальную машину в Cloud.ru с Ubuntu 22.04

🤖 Агент думает...
[Агент читает SKILL.md → определяет cloudru-vm → загружает навык → 
 проверяет переменные окружения → выполняет команду]

🤖 Агент: Для создания ВМ мне нужны переменные окружения:
- CP_CONSOLE_KEY_ID
- CP_CONSOLE_SECRET  
- PROJECT_ID

Проверяю... ❌ Переменные не настроены. 

Пожалуйста, настройте их в файле `.env`:
```
CP_CONSOLE_KEY_ID=your-key-id
CP_CONSOLE_SECRET=your-secret
PROJECT_ID=your-project-uuid
```

После настройки я выполню:
```bash
python vm.py create --name my-vm --flavor-name lowcost10-2-4 \
  --image-name ubuntu-22.04 --zone-name ru.AZ-1 \
  --disk-size 20 --disk-type-name SSD \
  --login user1 --ssh-key-file ~/.ssh/id_ed25519.pub \
  --wait --floating-ip --wait-ssh
```
```

### Пример 2: Браузерная автоматизация

```
 Вы: Открой GitHub и сделай скриншот

🤖 Агент думает...
[Агент загружает browser-use → выполняет команды]

🤖 Агент: ✅ Выполняю:
1. browser-use open https://github.com
2. browser-use screenshot github.png

Скриншот сохранён в github.png
```

---

## 🔑 Ключевые моменты

1. **Tool-calling**: Агент сам решает, какой инструмент вызвать на основе контекста
2. **Чтение навыков**: Агент сначала читает `SKILL.md`, потом загружает нужный навык
3. **Проверка зависимостей**: Перед выполнением проверяет переменные окружения
4. **Безопасность**: Не выводит секреты, спрашивает подтверждение для деструктивных операций
5. **Гибкость**: Можно добавить любые инструменты (API-клиенты, базы данных и т.д.)

---

## 🚀 Запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
echo "OPENAI_API_KEY=sk-..." > .env

# Запуск агента
python agent.py
```

Готово! Теперь у вас есть полноценный агент, который читает навыки и выполняет их через инструменты. 🎉