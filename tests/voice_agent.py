#!/usr/bin/env python3
#pip install aiohttp yandex-ai-studio-sdk


from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys

import aiohttp

from yandex_ai_studio_sdk._experimental.audio.microphone import AsyncMicrophone
from yandex_ai_studio_sdk._experimental.audio.out import AsyncAudioOut

assert sys.version_info >= (3, 10), "Python 3.10+ is required"


YANDEX_CLOUD_FOLDER_ID = "b1gd8itqunasnf56lij4"
YANDEX_CLOUD_API_KEY = "***…oh59V0"
YANDEX_REALTIME_MODEL = "speech-realtime-250923/latest"

PROMPT_ID = "aipsde4c3nltv4qk5b8i"

assert YANDEX_CLOUD_FOLDER_ID and YANDEX_CLOUD_API_KEY, (
	"YANDEX_CLOUD_FOLDER_ID и YANDEX_CLOUD_API_KEY обязательны"
)

WSS_URL = (
	"wss://ai.api.cloud.yandex.net/v1/realtime"
	f"?model=gpt://{YANDEX_CLOUD_FOLDER_ID}/{YANDEX_REALTIME_MODEL}"
)

HEADERS = {"Authorization": f"Api-Key {YANDEX_CLOUD_API_KEY}"}


def b64_decode(s: str) -> bytes:
	return base64.b64decode(s)


def b64_encode(b: bytes) -> str:
	return base64.b64encode(b).decode("ascii")


logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s - %(levelname)s - %(message)s",
	datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def process_function_call(item: dict) -> dict:
	call_id = item.get("call_id")
	return {
		"type": "conversation.item.create",
		"item": {
			"type": "function_call_output",
			"call_id": call_id,
			"output": json.dumps({"ok": True}, ensure_ascii=False),
		},
	}


async def setup_session(ws: aiohttp.ClientWebSocketResponse) -> None:
	prompt_obj: dict[str, object] = {
		"id": PROMPT_ID,
		"variables": {
			"company_name": "...",
			"product_name": "..."
		}
	}
	await ws.send_json(
		{
			"type": "session.update",
			"session": {
				"prompt": prompt_obj,
			},
		}
	)

	logger.info("Отправлен session.update с prompt.id=%r", PROMPT_ID)


async def downlink(ws: aiohttp.ClientWebSocketResponse, audio_out: AsyncAudioOut) -> None:
	play_epoch = 0
	current_response_epoch = None

	async for msg in ws:
		if msg.type != aiohttp.WSMsgType.TEXT:
			logger.info("got non-text payload from websocket: %s", msg.data)
			continue

		message = json.loads(msg.data)
		msg_type = message.get("type")

		match msg_type:
			case "session.created":
				session_id = (message.get("session") or {}).get("id")
				logger.info("on_message %s: [session.id = %r]", msg_type, session_id)

			case "session.updated":
				logger.info("on_message %s: session prompt applied", msg_type)

			case "conversation.item.input_audio_transcription.completed":
				transcript = message.get("transcript", "")
				if transcript:
					logger.info("on_message %s: [user (transcript): %r]", msg_type, transcript)

			case "response.output_text.delta":
				delta = message.get("delta", "")
				if delta:
					logger.info("on_message %s: [agent (text): %r]", msg_type, delta)

			case "input_audio_buffer.speech_started":
				play_epoch += 1
				current_response_epoch = None
				logger.debug("on_message %s: clear audio out buffer", msg_type)
				await audio_out.clear()

			case "response.created":
				current_response_epoch = play_epoch

			case "response.output_audio.delta":
				if current_response_epoch == play_epoch:
					delta = message.get("delta")
					if delta:
						decoded = b64_decode(delta)
						logger.debug("on_message %s: got %d bytes", msg_type, len(decoded))
						await audio_out.write(decoded)

			case "response.output_item.done":
				item = message.get("item") or {}
				if item.get("type") != "function_call":
					logger.info(
						"on_message %s: got non-function call payload %r",
						msg_type,
						item,
					)
					continue

				payload_item = process_function_call(item)
				logger.info("[conversation.item.create(function_call_output): %r]", payload_item)
				await ws.send_json(payload_item)

				logger.info("отправляем response.create после функции")
				await ws.send_json({"type": "response.create"})

			case "error":
				logger.error("ОШИБКА СЕРВЕРА: %r", json.dumps(message, ensure_ascii=False))

			case other:
				logger.info("on_message %s: [можно добавить ваш обработчик]", other)

	logger.info("WS соединение закрыто")


async def uplink(ws: aiohttp.ClientWebSocketResponse) -> None:
	mic = AsyncMicrophone(samplerate=44100)
	async for pcm in mic:
		logger.debug("send payload with size %d", len(pcm))

		try:
			await ws.send_json(
				{
					"type": "input_audio_buffer.append",
					"audio": b64_encode(pcm),
				}
			)
		except aiohttp.ClientConnectionResetError:
			logger.warning("unable to send new data due to websocket was closed")
			return


async def main() -> None:
	print("Говорите (server VAD). Выход: Ctrl+C.")

	try:
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect(WSS_URL, headers=HEADERS, heartbeat=20.0) as ws:
				logger.info("Подключено к Realtime API.")
				await setup_session(ws)

				async with AsyncAudioOut(samplerate=44100) as audio_out:
					await asyncio.gather(
						uplink(ws),
						downlink(ws, audio_out),
					)
	except (KeyboardInterrupt, asyncio.CancelledError):
		pass
	finally:
		logger.info("Выход.")


if __name__ == "__main__":
	asyncio.run(main())
	