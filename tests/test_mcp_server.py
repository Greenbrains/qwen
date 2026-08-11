"""
Тесты для проверки MCP-сервера Туту
Проверяет доступность эндпоинта и наличие необходимых инструментов
"""

import requests
import json


def check_mcp_server():
    """Проверка доступности MCP-сервера и списка инструментов"""
    mcp_url = "https://mcp.tutu.ru/mcp"
    
    # ВАЖНО: добавляем заголовки
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Запрос на инициализацию
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "hackathon-test",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        print(f"🔌 Подключение к MCP-серверу: {mcp_url}\n")
        
        # Инициализация с заголовками
        response = requests.post(mcp_url, json=init_payload, headers=headers, timeout=15)
        print(f"✅ Статус инициализации: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ MCP-сервер доступен\n")
            
            # Запрос списка инструментов с заголовками
            tools_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
            
            tools_response = requests.post(mcp_url, json=tools_payload, headers=headers, timeout=30)
            
            if tools_response.status_code == 200:
                tools_data = tools_response.json()
                tools = tools_data.get("result", {}).get("tools", [])
                
                print(f"📋 Найдено инструментов: {len(tools)}\n")
                print("📦 Список доступных инструментов:\n")
                
                for tool in tools:
                    name = tool.get('name', 'N/A')
                    desc = tool.get('description', 'Нет описания')[:100]
                    print(f"  • {name}")
                    print(f"    {desc}...\n")
                
                # Проверка наличия ключевых инструментов
                tool_names = [t.get("name") for t in tools]
                required_tools = [
                    "search_avia",
                    "search_rail",
                    "search_hotels",
                    "search_bus",
                    "search_multitransport",
                    "get_offer_details",
                    "create_checkout_link"
                ]
                
                missing = [t for t in required_tools if t not in tool_names]
                if missing:
                    print(f"⚠️  Отсутствуют инструменты: {', '.join(missing)}\n")
                    return None
                else:
                    print("✅ Все ключевые инструменты присутствуют\n")
                    return tools
            else:
                print(f"❌ Ошибка получения списка инструментов: {tools_response.status_code}")
                print(f"Response: {tools_response.text[:500]}\n")
        else:
            print(f"❌ Ошибка подключения: {response.status_code}")
            print(f"Response: {response.text[:500]}\n")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка сети: {e}")
    
    return None


def run_all_mcp_tests() -> bool:
    """
    Обёртка для main.py — запускает все тесты MCP-сервера.
    Возвращает True если все тесты пройдены, иначе False.
    """
    print("=" * 60)
    print("🧪 ЗАПУСК ТЕСТОВ MCP-СЕРВЕРА TUTU")
    print("=" * 60 + "\n")
    
    tools = check_mcp_server()
    
    if tools is not None and len(tools) > 0:
        print("=" * 60)
        print("✅ Все тесты MCP-сервера пройдены!")
        print("=" * 60 + "\n")
        return True
    else:
        print("=" * 60)
        print("❌ Тесты MCP-сервера не пройдены")
        print("=" * 60 + "\n")
        return False


if __name__ == "__main__":
    run_all_mcp_tests()