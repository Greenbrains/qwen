"""
Тесты создания агента через Yandex AI Studio Responses API
"""

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# ============================================================
# КОНСТАНТЫ — меняем руками при смене месяца
# ============================================================
API_KEY_ENV_NAME = "august2026"  # <-- меняйте тут при смене месяца
# ============================================================


def test_env_loading():
    """Тест 1: Загрузка .env файла"""
    print("📄 Тест 1: Загрузка .env файла")
    
    env_path = Path(".env")
    if not env_path.exists():
        print(f"   ❌ Файл .env не найден в корне проекта")
        print(f"      Путь: {env_path.absolute()}\n")
        return False
    
    if not DOTENV_AVAILABLE:
        print("   ❌ Пакет python-dotenv не установлен")
        print("   💡 Установите: pip install python-dotenv\n")
        return False
    
    load_dotenv(env_path, override=True)
    print(f"   ✅ .env файл загружен\n")
    return True


def test_api_key():
    """
    Тест 2: Проверка API-ключа.
    Имя переменной задано константой API_KEY_ENV_NAME.
    """
    print("🔑 Тест 2: Проверка API-ключа")
    print(f"   📌 Ищем переменную: {API_KEY_ENV_NAME}")
    
    api_key = os.environ.get(API_KEY_ENV_NAME)
    
    if not api_key:
        print(f"   ❌ Переменная '{API_KEY_ENV_NAME}' не найдена")
        print(f"   💡 Добавьте в .env строку: {API_KEY_ENV_NAME}=ваш_ключ\n")
        return False
    
    masked = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
    print(f"   ✅ API-ключ найден: {masked}\n")
    return True


def test_folder_id():
    """Тест 3: Проверка YANDEX_FOLDER_ID"""
    print("📁 Тест 3: Проверка YANDEX_FOLDER_ID")
    
    folder_id = os.environ.get("YANDEX_FOLDER_ID")
    
    if not folder_id:
        print("   ❌ YANDEX_FOLDER_ID не найден в .env\n")
        return False
    
    print(f"   ✅ YANDEX_FOLDER_ID: {folder_id}\n")
    return True


def test_model_config():
    """Тест 4: Проверка имени модели и формирование составной модели"""
    print("🤖 Тест 4: Проверка модели")
    
    model_name = os.environ.get("YANDEX_MODEL")
    folder_id = os.environ.get("YANDEX_FOLDER_ID")
    
    if not model_name:
        print("   ❌ YANDEX_MODEL не найден в .env\n")
        return False
    
    if not folder_id:
        print("   ⚠️  Модель найдена, но YANDEX_FOLDER_ID отсутствует")
        print(f"      YANDEX_MODEL: {model_name}\n")
        return False
    
    composite_model = f"gpt://{folder_id}/{model_name}"
    print(f"   ✅ YANDEX_MODEL: {model_name}")
    print(f"   ✅ Составная модель: {composite_model}\n")
    return True


def test_mcp_config_file():
    """Тест 5: Проверка файла конфигурации MCP Tool"""
    print("🔧 Тест 5: Проверка конфигурации MCP Tool")
    config_path = os.path.join("tools", "mcp_tutu.config.json")
    
    if not os.path.exists(config_path):
        print(f"   ❌ Файл не найден: {config_path}\n")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        required_fields = ["type", "server_url", "server_label"]
        missing = [f for f in required_fields if f not in config]
        
        if missing:
            print(f"   ❌ Отсутствуют поля: {', '.join(missing)}\n")
            return False
        
        print(f"   ✅ Конфиг валиден")
        print(f"      📡 Server URL: {config.get('server_url')}")
        print(f"      🏷️  Label: {config.get('server_label')}\n")
        return True
    except json.JSONDecodeError as e:
        print(f"   ❌ Ошибка JSON: {e}\n")
        return False


def test_dependencies():
    """Тест 6: Проверка зависимостей"""
    print("📦 Тест 6: Проверка зависимостей")
    
    required = {
        "openai": "pip install openai",
        "requests": "pip install requests",
        "dotenv": "pip install python-dotenv",
    }
    
    all_ok = True
    for package, install_cmd in required.items():
        try:
            mod = __import__(package)
            version = getattr(mod, "__version__", "unknown")
            print(f"   ✅ {package} ({version})")
        except ImportError:
            print(f"   ❌ {package} не установлен")
            print(f"      💡 {install_cmd}")
            all_ok = False
    
    print("")
    return all_ok


def run_all_agent_tests() -> bool:
    """Запуск всех тестов создания агента"""
    print("=" * 60)
    print("🤖 ЗАПУСК ТЕСТОВ СОЗДАНИЯ АГЕНТА")
    print("=" * 60 + "\n")
    
    results = [
        ("Загрузка .env", test_env_loading()),
        ("API-ключ", test_api_key()),
        ("YANDEX_FOLDER_ID", test_folder_id()),
        ("Модель (YANDEX_MODEL)", test_model_config()),
        ("MCP Tool config", test_mcp_config_file()),
        ("Зависимости", test_dependencies()),
    ]
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("=" * 60)
    print(f"📊 Результат: {passed}/{total}")
    print("=" * 60 + "\n")
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    print("")
    
    if passed == total:
        print("✅ Все проверки пройдены!\n")
        return True
    else:
        print(f"⚠️  Не пройдено: {total - passed}\n")
        return False


if __name__ == "__main__":
    run_all_agent_tests()

