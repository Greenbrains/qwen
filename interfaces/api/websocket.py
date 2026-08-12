"""
WebSocket эндпоинты.
/ws       — текстовый чат с агентом (JSON {"type":"text","message":...}).
/ws/voice — голосовой режим для браузера (push-to-talk):
            браузер шлёт PCM16 base64 -> сервер проксирует в Yandex Realtime API,
            выполняет MCP function_call и возвращает аудио/текст обратно.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging

import aiohttp
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from interfaces.api.handlers import handle_function_call
from interfaces.dependencies import get_dependencies

logger = logging.getLogger("travel_agent.api.websocket")
router = APIRouter()


def resample_pcm16(pcm16_bytes: bytes, from_rate: int, to_rate: int) -> bytes:
    """
    Простой линейный ресемплинг PCM16 little-endian.
    Если частоты совпадают — возвращает исходные байты.
    """
    if from_rate == to_rate:
        return pcm16_bytes

    import struct
    
    # Декодируем в массив int16
    samples = struct.unpack(f'<{len(pcm16_bytes) // 2}h', pcm16_bytes)
    
    # Ресемплинг
    ratio = from_rate / to_rate
    new_length = int(len(samples) / ratio)
    new_samples = []
    
    for i in range(new_length):
        src_idx = i * ratio
        idx = int(src_idx)
        frac = src_idx - idx
        
        if idx + 1 < len(samples):
            # Линейная интерполяция
            s1 = samples[idx]
            s2 = samples[idx + 1]
            new_samples.append(int(s1 + (s2 - s1) * frac))
        elif idx < len(samples):
            new_samples.append(samples[idx])
        else:
            break
    
    # Упаковываем обратно в bytes
    return struct.pack(f'<{len(new_samples)}h', *new_samples)


# ----------------------------------------------------------------------
# /ws — текстовый чат
# ----------------------------------------------------------------------
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Текстовый чат: идёт через оркестратор, как REST /chat и CLI."""
    await websocket.accept()
    deps = get_dependencies()
    if deps.orchestrator is None:
        await websocket.send_json({"type": "error", "message": "Оркестратор не инициализирован"})
        await websocket.close()
        return
    session = deps.session_store.get_or_create()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                message = {"type": "text", "message": data}
            msg_type = message.get("type", "text")
            if msg_type == "text":
                user_text = message.get("message", "")
                last_agent = getattr(session, "last_agent", None)
                final_text, new_history, tool_calls, agent_name = await deps.orchestrator.run(
                    user_text, session.history, last_agent
                )
                session.messages = new_history
                session.last_agent = agent_name
                session.record_tool_calls(tool_calls)
                deps.session_store.save(session)
                await websocket.send_json({
                    "type": "text",
                    "message": final_text,
                    "session_id": session.session_id,
                    "agent_name": agent_name,
                    "tool_calls": len(tool_calls),
                })
            elif msg_type == "clear":
                session.clear()
                await websocket.send_json({"type": "cleared"})
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Неизвестный тип сообщения: {msg_type}",
                })
    except WebSocketDisconnect:
        logger.info("WebSocket /ws disconnected")
    except Exception as e:
        logger.error(f"WebSocket /ws error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# ----------------------------------------------------------------------
# /ws/voice — голосовой режим (браузер <-> Yandex Realtime API)
# ----------------------------------------------------------------------
@router.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    """
    Голосовой прокси для браузера.
    Браузер шлёт PCM16 на 44.1 кГц (как в эталоне SDK).
    Если частота другая — ресемплим на лету.
    """
    await websocket.accept()
    deps = get_dependencies()

    agent = getattr(deps, "agent", None)
    mcp_client = getattr(deps, "mcp_client", None)

    # Целевая частота для Yandex Realtime (как в эталоне: 44100 Гц)
    TARGET_SAMPLE_RATE = 44100

    async with aiohttp.ClientSession() as http:
        yws = None
        try:
            yws = await http.ws_connect(
                deps.settings.realtime_ws_url,
                headers=deps.settings.realtime_headers,
                heartbeat=20.0,
            )
            logger.info("Подключено к Yandex Realtime API")

            # Конфигурация Realtime-сессии
            session_payload: dict = {
                "modalities": ["text", "audio"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                # push-to-turn: браузер сам шлёт audio_end
                "turn_detection": None,
            }

            if deps.settings.yandex_realtime_prompt_id:
                session_payload["prompt"] = {
                    "id": deps.settings.yandex_realtime_prompt_id,
                    "variables": {
                        "company_name": "Туту",
                        "product_name": "Travel Agent",
                    },
                }
                logger.info(
                    "Отправлен session.update с prompt.id=%r",
                    deps.settings.yandex_realtime_prompt_id,
                )
            elif agent is not None:
                session_payload["instructions"] = getattr(agent, "system_prompt", "")

            await yws.send_json({
                "type": "session.update",
                "session": session_payload,
            })
            await websocket.send_json({"type": "voice_ready"})

            # --- клиент (браузер) -> Яндекс ---
            async def client_to_yandex():
                while True:
                    try:
                        m = await websocket.receive_json()
                    except Exception as e:
                        logger.debug(f"Error receiving from browser: {e}")
                        return

                    t = m.get("type")

                    if t == "audio":
                        base64_audio = m.get("data", "")
                        browser_sample_rate = m.get("sample_rate", TARGET_SAMPLE_RATE)

                        # Декодируем base64
                        try:
                            pcm_bytes = base64.b64decode(base64_audio)
                        except Exception as e:
                            logger.warning(f"Invalid base64 audio: {e}")
                            continue

                        # Ресемплим, если частота браузера != целевой
                        if browser_sample_rate != TARGET_SAMPLE_RATE:
                            logger.debug(
                                f"Resampling {browser_sample_rate} -> {TARGET_SAMPLE_RATE}"
                            )
                            pcm_bytes = resample_pcm16(
                                pcm_bytes, browser_sample_rate, TARGET_SAMPLE_RATE
                            )

                        # Кодируем обратно в base64
                        resampled_base64 = base64.b64encode(pcm_bytes).decode("ascii")

                        try:
                            await yws.send_json({
                                "type": "input_audio_buffer.append",
                                "audio": resampled_base64,
                            })
                        except (aiohttp.ClientConnectionError, ConnectionError) as e:
                            logger.warning(f"Cannot send audio to Yandex: {e}")
                            return

                    elif t == "audio_end":
                        try:
                            await yws.send_json({"type": "input_audio_buffer.commit"})
                            await yws.send_json({"type": "response.create"})
                        except (aiohttp.ClientConnectionError, ConnectionError) as e:
                            logger.warning(f"Cannot send audio_end to Yandex: {e}")
                            return

                    elif t == "text":
                        try:
                            await yws.send_json({
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [{"type": "input_text", "text": m.get("text", "")}],
                                },
                            })
                            await yws.send_json({"type": "response.create"})
                        except (aiohttp.ClientConnectionError, ConnectionError) as e:
                            logger.warning(f"Cannot send text to Yandex: {e}")
                            return

            # --- Яндекс -> клиент (браузер) ---
            async def yandex_to_client():
                try:
                    async for msg in yws:
                        if msg.type != aiohttp.WSMsgType.TEXT:
                            logger.debug(f"Non-text message from Yandex: {msg.type}")
                            continue

                        try:
                            ev = json.loads(msg.data)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from Yandex: {msg.data[:200]}")
                            continue

                        t = ev.get("type")

                        if t == "session.created":
                            sid = (ev.get("session") or {}).get("id")
                            logger.info(f"session.created: id={sid}")

                        elif t == "session.updated":
                            logger.info("session.updated: prompt applied")

                        elif t == "conversation.item.input_audio_transcription.completed":
                            transcript = ev.get("transcript", "")
                            if transcript:
                                logger.info(f"user (transcript): {transcript}")
                                try:
                                    await websocket.send_json({"type": "user_text", "text": transcript})
                                except Exception:
                                    pass

                        elif t == "response.output_text.delta":
                            delta = ev.get("delta", "")
                            if delta:
                                logger.debug(f"agent (text): {delta}")
                                try:
                                    await websocket.send_json({"type": "text_delta", "text": delta})
                                except Exception:
                                    pass

                        elif t == "input_audio_buffer.speech_started":
                            logger.debug("speech_started")

                        elif t == "response.created":
                            logger.debug("response.created")

                        elif t == "response.output_audio.delta":
                            delta = ev.get("delta")
                            if delta:
                                try:
                                    await websocket.send_json({
                                        "type": "audio_delta",
                                        "data": delta,
                                    })
                                except Exception:
                                    pass

                        elif t == "response.output_item.done":
                            item = ev.get("item") or {}
                            if item.get("type") == "function_call":
                                try:
                                    await websocket.send_json({
                                        "type": "tool_call",
                                        "name": item.get("name"),
                                        "call_id": item.get("call_id"),
                                    })
                                    await handle_function_call(yws, item, mcp_client, http)
                                except Exception as e:
                                    logger.error(f"Error handling function call: {e}", exc_info=True)

                        elif t == "response.done":
                            try:
                                await websocket.send_json({"type": "response_done"})
                            except Exception:
                                pass

                        elif t == "error":
                            err = ev.get("error") or {}
                            logger.error(f"Yandex Realtime error: {err}")
                            try:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": err.get("message", str(ev)),
                                })
                            except Exception:
                                pass

                        else:
                            logger.debug(f"Unhandled Yandex event: {t}")

                except aiohttp.ClientConnectionError as e:
                    logger.info(f"Yandex connection closed: {e}")
                except Exception as e:
                    logger.error(f"Error in yandex_to_client: {e}", exc_info=True)

            tasks = [
                asyncio.create_task(client_to_yandex()),
                asyncio.create_task(yandex_to_client()),
            ]
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logger.debug("Voice tasks cancelled")
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()

        except aiohttp.ClientConnectionError as e:
            logger.error(f"Не удалось подключиться к Yandex Realtime API: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Не удалось подключиться к Yandex API: {e}",
                })
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Voice mode error: {e}", exc_info=True)
            try:
                await websocket.send_json({"type": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            try:
                await websocket.close()
            except Exception:
                pass
            if yws and not yws.closed:
                try:
                    await yws.close()
                except Exception:
                    pass