"""
main_tests.py

Полная проверка MCP-сервера Туту:
1) DNS/TCP доступность
2) HTTP доступность endpoint
3) MCP initialize
4) MCP tools/list
5) вызов всех 16 инструментов с реальной передачей параметров

Особенность: create_checkout_link требует плоской структуры аргументов
(без вложенного checkout_ref), поэтому поля из checkout_ref извлекаются
из search-ответов и подмешиваются на верхний уровень.

Используется только стандартная библиотека Python.
Отчёт сохраняется в mcp_server_check_report.json.
"""

import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ============================================================
# Настройки
# ============================================================

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://mcp.tutu.ru/mcp").strip()

try:
    MCP_TIMEOUT = int(os.environ.get("MCP_TIMEOUT", "120"))
except Exception:
    MCP_TIMEOUT = 120

MCP_PROTOCOL_VERSION = os.environ.get("MCP_PROTOCOL_VERSION", "2024-11-05")
MCP_EXTRA_HEADERS = os.environ.get("MCP_EXTRA_HEADERS", "")
REPORT_FILE = os.environ.get("MCP_REPORT_FILE", "mcp_server_check_report.json")


def make_ssl_context():
    ctx = ssl.create_default_context()
    if os.environ.get("MCP_INSECURE_SSL", "") == "1":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


SSL_CONTEXT = make_ssl_context()
_EXTRA_HEADERS_CACHE = None


# ============================================================
# Реальные сигнатуры 16 инструментов (исправлено по ошибкам Pydantic)
# ============================================================

MCP_16_TOOL_REQUESTS = [
    # 1. search_hotels — БЕЗ guests
    {
        "name": "search_hotels",
        "arguments": {
            "city_name": "Санкт-Петербург",
            "check_in": "2026-08-10",
            "check_out": "2026-08-15"
        }
    },
    # 2. search_avia — БЕЗ passengers
    {
        "name": "search_avia",
        "arguments": {
            "origin": "Москва",
            "destination": "Сочи",
            "departure_date": "2026-08-20"
        }
    },
    # 3. search_rail
    {
        "name": "search_rail",
        "arguments": {
            "origin": "Москва",
            "destination": "Казань",
            "departure_date": "2026-08-25"
        }
    },
    # 4. search_bus
    {
        "name": "search_bus",
        "arguments": {
            "origin": "Екатеринбург",
            "destination": "Челябинск",
            "departure_date": "2026-08-12"
        }
    },
    # 5. search_etrain
    {
        "name": "search_etrain",
        "arguments": {
            "origin": "Москва",
            "destination": "Сергиев Посад",
            "departure_date": "2026-08-05"
        }
    },
    # 6. search_multitransport
    {
        "name": "search_multitransport",
        "arguments": {
            "origin": "Новосибирск",
            "destination": "Томск",
            "departure_date": "2026-09-01",
            "optimize_for": "price"
        }
    },
    # 7. get_offer_details — product_type + details_ref (подставим из search_rail)
    {
        "name": "get_offer_details",
        "arguments": {
            "product_type": "rail",
            "details_ref": "{{RAIL_DETAILS_REF}}",
            "view": "full"
        }
    },
    # 8. get_rail_seatmap — details_ref + car_number (STRING!)
    {
        "name": "get_rail_seatmap",
        "arguments": {
            "details_ref": "{{RAIL_DETAILS_REF}}",
            "car_number": "1"
        }
    },
    # 9–14. Инструкции
    {"name": "get_avia_instructions", "arguments": {}},
    {"name": "get_rail_instructions", "arguments": {}},
    {"name": "get_bus_instructions", "arguments": {}},
    {"name": "get_etrain_instructions", "arguments": {}},
    {"name": "get_hotels_instructions", "arguments": {}},
    {"name": "get_multitransport_instructions", "arguments": {}},
    # 15. create_checkout_link — product_type + passengers (int!)
    # Поля из checkout_ref подмешиваются динамически в цикле
    {
        "name": "create_checkout_link",
        "arguments": {
            "product_type": "rail",
            "passengers": 1
        }
    },
    # 16. fetch_resource — реальный URI
    {
        "name": "fetch_resource",
        "arguments": {
            "uri": "tutu://amenities/dictionary"
        }
    }
]

EXPECTED_TOOLS = [tool["name"] for tool in MCP_16_TOOL_REQUESTS]


# ============================================================
# Вспомогательные функции
# ============================================================

def print_sep(char="-"):
    print(char * 70)


def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def truncate(value, limit=4000):
    if value is None:
        return ""
    if not isinstance(value, str):
        try:
            value = json.dumps(value, ensure_ascii=False, indent=2)
        except Exception:
            value = str(value)
    if len(value) > limit:
        return value[:limit] + f"\n... обрезано {len(value) - limit} символов"
    return value


def get_extra_headers():
    global _EXTRA_HEADERS_CACHE
    if _EXTRA_HEADERS_CACHE is None:
        _EXTRA_HEADERS_CACHE = {}
        if MCP_EXTRA_HEADERS:
            try:
                parsed = json.loads(MCP_EXTRA_HEADERS)
                if isinstance(parsed, dict):
                    _EXTRA_HEADERS_CACHE = {str(k): str(v) for k, v in parsed.items()}
            except Exception as e:
                print(f"⚠️  Не удалось распарсить MCP_EXTRA_HEADERS: {e}")
    return _EXTRA_HEADERS_CACHE


def parse_headers(headers):
    try:
        return {k: v for k, v in headers.items()}
    except Exception:
        return {}


def parse_body(body, headers):
    headers_lower = {}
    try:
        headers_lower = {str(k).lower(): str(v) for k, v in (headers or {}).items()}
    except Exception:
        pass

    content_type = headers_lower.get("content-type", "")

    result = {
        "empty": not bool(body and body.strip()),
        "format": "unknown",
        "body": None,
        "raw_preview": (body or "")[:5000],
    }

    if result["empty"]:
        return result

    # 1) JSON
    if "application/json" in content_type or body.lstrip()[:1] in ("{", "["):
        try:
            result["body"] = json.loads(body)
            result["format"] = "json"
            return result
        except Exception:
            pass

    # 2) SSE
    if (
        "text/event-stream" in content_type
        or body.lstrip().startswith(("event:", "data:"))
        or "\ndata:" in body
    ):
        events = []
        for raw_line in body.splitlines():
            raw_line = raw_line.strip()
            if raw_line.startswith("data:"):
                data = raw_line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try:
                    events.append(json.loads(data))
                except Exception:
                    pass
        if events:
            result["format"] = "sse-json"
            result["sse_events"] = len(events)
            selected = None
            for event in reversed(events):
                if isinstance(event, dict) and ("result" in event or "error" in event):
                    selected = event
                    break
            result["body"] = selected if selected is not None else events[-1]
            return result
        result["format"] = "sse"
        return result

    return result


def http_request(url, method="GET", headers=None, timeout=30):
    headers = headers or {}
    req = urllib.request.Request(url, method=method, headers=headers)
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
            body = resp.read().decode("utf-8", "replace")
            elapsed_ms = int((time.time() - start) * 1000)
            return {
                "ok": True, "status": resp.status,
                "headers": parse_headers(resp.headers),
                "body": body, "elapsed_ms": elapsed_ms, "error": None,
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "ok": False, "status": e.code,
            "headers": parse_headers(e.headers),
            "body": body, "elapsed_ms": elapsed_ms,
            "error": f"HTTP {e.code} {e.reason}",
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "ok": False, "status": None, "headers": {},
            "body": "", "elapsed_ms": elapsed_ms, "error": str(e),
        }


def post_jsonrpc(url, payload, session_id=None, timeout=MCP_TIMEOUT):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        "User-Agent": "main-tests/1.0",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    headers.update(get_extra_headers())

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    start = time.time()
    network_error = None

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
            body = resp.read().decode("utf-8", "replace")
            status = resp.status
            resp_headers = parse_headers(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        status = e.code
        resp_headers = parse_headers(e.headers)
        network_error = f"HTTP Error {e.code} {e.reason}"
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "ok": False, "status": None, "headers": {},
            "raw_full": "", "parsed": parse_body("", {}),
            "body": None, "elapsed_ms": elapsed_ms,
            "session_id": session_id, "network_error": str(e),
            "request": payload,
        }

    elapsed_ms = int((time.time() - start) * 1000)
    parsed = parse_body(body, resp_headers)

    session_id_out = session_id
    for k, v in resp_headers.items():
        if str(k).lower() == "mcp-session-id" and v:
            session_id_out = v
            break

    ok = False
    if status is not None:
        if status == 202:
            ok = True
        elif status == 200 and not parsed["empty"]:
            ok = True

    return {
        "ok": ok, "status": status, "headers": resp_headers,
        "raw_full": body, "parsed": parsed,
        "body": parsed.get("body"),
        "elapsed_ms": elapsed_ms, "session_id": session_id_out,
        "network_error": network_error, "request": payload,
    }


def is_jsonrpc_success(resp):
    if resp.get("network_error"):
        return False
    body = resp.get("body")
    if not isinstance(body, dict):
        return False
    if body.get("error"):
        return False
    result = body.get("result")
    if isinstance(result, dict) and result.get("isError"):
        return False
    return "result" in body


def response_received(resp):
    return resp.get("status") is not None and not resp.get("parsed", {}).get("empty", True)


def check_network(url):
    parsed = urlparse(url)
    if not parsed.hostname:
        print(f"❌ Неверный URL: {url}")
        return False

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    print(f"Цель: {host}:{port}")

    try:
        addrinfo = socket.getaddrinfo(host, port)
        first_ip = addrinfo[0][4][0] if addrinfo else "unknown"
        print(f"✅ DNS OK, первый адрес: {first_ip}")
    except Exception as e:
        print(f"❌ DNS ошибка: {e}")
        return False

    try:
        with socket.create_connection((host, port), timeout=15):
            print("✅ TCP соединение OK")
            return True
    except Exception as e:
        print(f"❌ TCP ошибка: {e}")
        return False


def apply_state(value, state):
    """Подставляет {{KEY}} из state."""
    if isinstance(value, dict):
        return {k: apply_state(v, state) for k, v in value.items()}
    if isinstance(value, list):
        return [apply_state(v, state) for v in value]
    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        key = value[2:-2].strip()
        return state.get(key, value)
    return value


def extract_from_search_response(resp, tool_name):
    """
    Штатный парсер: пытается извлечь details_ref и checkout_ref через json.loads.
    """
    body = resp.get("body")
    if not isinstance(body, dict):
        return None, None

    result = body.get("result")
    if not isinstance(result, dict):
        return None, None

    content = result.get("content")
    if not isinstance(content, list) or not content:
        return None, None

    text = ""
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text":
            text = item.get("text", "")
            break

    if not text:
        return None, None

    try:
        data = json.loads(text)
    except Exception:
        return None, None

    offers = data.get("offers") or data.get("variants") or []
    if not isinstance(offers, list) or not offers:
        return None, None

    first = offers[0]
    if not isinstance(first, dict):
        return None, None

    details_ref = first.get("details_ref")
    checkout_ref = first.get("checkout_ref")

    return details_ref, checkout_ref


def extract_refs_via_regex(raw_full):
    """
    Fallback-парсер: извлекает первый details_ref и checkout_ref через regex.
    Используется, если штатный json.loads не срабатывает.
    """
    if not raw_full:
        return None, None

    def extract_first_block(key):
        pattern = rf'"{key}"\s*:\s*(\{{)'
        match = re.search(pattern, raw_full)
        if not match:
            return None
        start = match.end(1)
        depth = 1
        i = start
        while i < len(raw_full) and depth > 0:
            ch = raw_full[i]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            i += 1
        # i теперь на позиции сразу после закрывающей }
        block = raw_full[match.start(1) - 1:i]
        try:
            return json.loads(block)
        except Exception:
            return None

    details_ref = extract_first_block("details_ref")
    checkout_ref = extract_first_block("checkout_ref")

    return details_ref, checkout_ref


def flatten_checkout_ref(checkout_ref):
    """
    Возвращает плоский dict из checkout_ref — для подмешивания
    в arguments create_checkout_link.
    """
    if not isinstance(checkout_ref, dict):
        return {}
    return dict(checkout_ref)


def save_report(report):
    try:
        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n📄 Полный отчет сохранен: {REPORT_FILE}")
    except Exception as e:
        print(f"\n⚠️  Не удалось сохранить отчет: {e}")


# ============================================================
# Основной сценарий
# ============================================================

def main():
    print_sep("=")
    print("MCP SERVER FULL CHECK (FIXED SIGNATURES)")
    print_sep("=")

    print(f"Время запуска: {now_str()}")
    print(f"MCP_SERVER_URL: {MCP_SERVER_URL}")
    print(f"MCP_TIMEOUT: {MCP_TIMEOUT} сек")
    print(f"MCP_PROTOCOL_VERSION: {MCP_PROTOCOL_VERSION}")

    report = {
        "url": MCP_SERVER_URL,
        "started_at": now_str(),
        "protocol_version": MCP_PROTOCOL_VERSION,
        "steps": [],
        "tool_results": [],
        "summary": {},
    }

    if not MCP_SERVER_URL.startswith(("http://", "https://")):
        print("❌ MCP_SERVER_URL должен начинаться с http:// или https://")
        return 2

    # 1. DNS/TCP
    print("\n[1/5] Проверка DNS/TCP")
    print_sep()
    net_ok = check_network(MCP_SERVER_URL)
    report["steps"].append({"step": "network", "ok": net_ok})
    if not net_ok:
        save_report(report)
        return 1

    # 2. HTTP GET
    print("\n[2/5] HTTP доступность endpoint")
    print_sep()
    http_headers = {
        "Accept": "*/*", "User-Agent": "main-tests/1.0",
        "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    }
    http_headers.update(get_extra_headers())
    http_resp = http_request(MCP_SERVER_URL, method="GET",
                             headers=http_headers, timeout=min(MCP_TIMEOUT, 60))
    print(f"GET status: {http_resp.get('status')}")
    print(f"Body preview: {truncate(http_resp.get('body') or '', 1000)}")
    report["steps"].append({
        "step": "http_get", "status": http_resp.get("status"),
        "elapsed_ms": http_resp.get("elapsed_ms"),
        "error": http_resp.get("error"),
    })

    # 3. MCP initialize
    print("\n[3/5] MCP initialize")
    print_sep()
    init_payload = {
        "jsonrpc": "2.0", "id": "init-1",
        "method": "initialize",
        "params": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "main-tests", "version": "1.0.0"}
        }
    }
    init_resp = post_jsonrpc(MCP_SERVER_URL, init_payload)
    session_id = init_resp.get("session_id")
    print(f"HTTP status: {init_resp.get('status')}")
    print(f"initialize success: {is_jsonrpc_success(init_resp)}")
    if session_id:
        print(f"Mcp-Session-Id: {session_id}")

    # notifications/initialized
    notif_payload = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    post_jsonrpc(MCP_SERVER_URL, notif_payload, session_id)

    report["steps"].append({
        "step": "initialize",
        "ok": is_jsonrpc_success(init_resp),
        "status": init_resp.get("status"),
        "session_id": session_id,
    })

    # 4. tools/list
    print("\n[4/5] MCP tools/list")
    print_sep()
    list_payload = {
        "jsonrpc": "2.0", "id": "tools-list-1",
        "method": "tools/list", "params": {}
    }
    list_resp = post_jsonrpc(MCP_SERVER_URL, list_payload, session_id)
    session_id = list_resp.get("session_id") or session_id

    tool_names = []
    body = list_resp.get("body")
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, dict):
            for t in (result.get("tools") or []):
                if isinstance(t, dict) and t.get("name"):
                    tool_names.append(t.get("name"))

    print(f"Найдено инструментов: {len(tool_names)}")
    report["steps"].append({
        "step": "tools/list",
        "status": list_resp.get("status"),
        "tool_names": tool_names,
    })

    # 5. Вызов 16 инструментов
    print("\n[5/5] Вызов 16 инструментов")
    print_sep()

    # Состояние для подстановки details_ref и плоских полей checkout_ref
    state = {
        "RAIL_DETAILS_REF": None,
        "BUS_DETAILS_REF": None,

        "RAIL_CHECKOUT_FIELDS": {},
        "AVIA_CHECKOUT_FIELDS": {},
        "HOTELS_CHECKOUT_FIELDS": {},
        "BUS_CHECKOUT_FIELDS": {},
        "ETRAIN_CHECKOUT_FIELDS": {},
    }

    tool_results = []
    failures = []

    for idx, tool in enumerate(MCP_16_TOOL_REQUESTS, start=1):
        tool_name = tool["name"]
        arguments = apply_state(tool.get("arguments", {}), state)

        # ============================================================
        # СПЕЦИАЛЬНАЯ ОБРАБОТКА: create_checkout_link
        # Подмешиваем поля из checkout_ref на верхний уровень arguments,
        # потому что Pydantic-схема запрещает вложенный объект checkout_ref.
        # ============================================================
        if tool_name == "create_checkout_link":
            pt = arguments.get("product_type", "rail")
            fields_map = {
                "rail": "RAIL_CHECKOUT_FIELDS",
                "avia": "AVIA_CHECKOUT_FIELDS",
                "hotels": "HOTELS_CHECKOUT_FIELDS",
                "bus": "BUS_CHECKOUT_FIELDS",
                "etrain": "ETRAIN_CHECKOUT_FIELDS",
            }
            state_key = fields_map.get(pt, "RAIL_CHECKOUT_FIELDS")
            fields = state.get(state_key, {})

            if fields:
                arguments.update(fields)
                print(f"\n🔗 В create_checkout_link добавлено {len(fields)} полей из checkout_ref (product_type={pt})")
            else:
                print(f"\n⚠️  Нет полей для product_type={pt} в state — create_checkout_link почти наверняка упадёт")

        payload = {
            "jsonrpc": "2.0",
            "id": f"tool-{idx:02d}-{tool_name}",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }

        print_sep()
        print(f"[{idx:02d}/16] {tool_name}")
        print_sep()
        print("Request:")
        print(truncate(payload, 2500))

        resp = post_jsonrpc(MCP_SERVER_URL, payload, session_id)
        session_id = resp.get("session_id") or session_id

        received = response_received(resp)
        success = is_jsonrpc_success(resp)

        print(f"\nHTTP status: {resp.get('status')}")
        print(f"Elapsed: {resp.get('elapsed_ms')} ms")
        print(f"Ответ получен: {received}")
        print(f"Успех: {success}")

        if resp.get("network_error"):
            print(f"Ошибка сети: {resp.get('network_error')}")

        print("\nResponse:")
        output = resp.get("body") if resp.get("body") is not None else resp.get("raw_full")
        print(truncate(output, 4000))

        # ============================================================
        # Извлекаем details_ref / checkout_ref из search-ответов
        # Сначала штатный парсер, затем regex-fallback
        # ============================================================
        if tool_name.startswith("search_") and success:
            details_ref, checkout_ref = extract_from_search_response(resp, tool_name)

            # Regex-fallback если что-то не удалось
            if details_ref is None or checkout_ref is None:
                dr, cr = extract_refs_via_regex(resp.get("raw_full", ""))
                if details_ref is None:
                    details_ref = dr
                if checkout_ref is None:
                    checkout_ref = cr

            if details_ref:
                if tool_name == "search_rail":
                    state["RAIL_DETAILS_REF"] = details_ref
                    print(f"\n🪄 RAIL_DETAILS_REF извлечен ({len(details_ref)} полей)")
                elif tool_name == "search_bus":
                    state["BUS_DETAILS_REF"] = details_ref
                    print(f"\n🪄 BUS_DETAILS_REF извлечен ({len(details_ref)} полей)")

            if checkout_ref:
                flat = flatten_checkout_ref(checkout_ref)
                if tool_name == "search_rail":
                    state["RAIL_CHECKOUT_FIELDS"] = flat
                    print(f"🪄 RAIL_CHECKOUT_FIELDS извлечены ({len(flat)} полей)")
                elif tool_name == "search_avia":
                    state["AVIA_CHECKOUT_FIELDS"] = flat
                    print(f"🪄 AVIA_CHECKOUT_FIELDS извлечены ({len(flat)} полей)")
                elif tool_name == "search_hotels":
                    state["HOTELS_CHECKOUT_FIELDS"] = flat
                    print(f"🪄 HOTELS_CHECKOUT_FIELDS извлечены ({len(flat)} полей)")
                elif tool_name == "search_bus":
                    state["BUS_CHECKOUT_FIELDS"] = flat
                    print(f"🪄 BUS_CHECKOUT_FIELDS извлечены ({len(flat)} полей)")
                elif tool_name == "search_etrain":
                    state["ETRAIN_CHECKOUT_FIELDS"] = flat
                    print(f"🪄 ETRAIN_CHECKOUT_FIELDS извлечены ({len(flat)} полей)")
                elif tool_name == "search_multitransport":
                    # multitransport возвращает variants[], а не offers[]
                    # Берём первый variant для rail-полей
                    state["RAIL_CHECKOUT_FIELDS"] = flat
                    print(f"🪄 RAIL_CHECKOUT_FIELDS извлечены из multitransport ({len(flat)} полей)")

        tool_results.append({
            "index": idx, "name": tool_name,
            "http_status": resp.get("status"),
            "elapsed_ms": resp.get("elapsed_ms"),
            "received": received, "success": success,
            "network_error": resp.get("network_error"),
            "request": payload,
            "response_preview": (resp.get("raw_full") or "")[:8000],
        })

        if not received:
            failures.append(f"{tool_name}: пустой ответ")
        elif not success:
            failures.append(f"{tool_name}: MCP вернул ошибку")

    # Итоги
    received_count = sum(1 for x in tool_results if x["received"])
    success_count = sum(1 for x in tool_results if x["success"])

    print_sep("=")
    print("ИТОГ")
    print_sep("=")
    print(f"Всего инструментов: {len(tool_results)}")
    print(f"Непустой ответ: {received_count}/{len(tool_results)}")
    print(f"Успешных: {success_count}/{len(tool_results)}")

    if failures:
        print("\nПроблемы:")
        for f in failures:
            print(f" - {f}")

    report["tool_results"] = tool_results
    report["summary"] = {
        "total_tools": len(tool_results),
        "received_count": received_count,
        "success_count": success_count,
        "failures": failures,
        "finished_at": now_str(),
    }
    save_report(report)

    if success_count == len(tool_results):
        print("\n🎉 Все 16 инструментов отработали успешно!")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())