# ============================================================
# orchestrator.py — агент-оркестратор мультиагентной системы
#
# Роль: принять запрос пользователя, декомпозировать его, выбрать навык(и),
# СГЕНЕРИРОВАТЬ системный промпт для агента-исполнителя и запустить его.
# Исполнители имеют СВОИ скиллы (ограниченный набор инструментов из
# SKILL_TOOLSETS) — оркестратор лишь диктует им инструкцию (system prompt).
#
# Оркестратор сам инструментов предметной области не имеет — он «менеджер».
# ============================================================
import json
import logging
from typing import List

from openai import OpenAI

from agent import client, MODEL_URI, GENERATION, spawn_executor, load_skills_catalog
from agent_tools import _short_text

logger = logging.getLogger("agent.orchestrator")

# Мета-промпт: оркестратор ДОЛЖЕН вернуть JSON-план.
ORCHESTRATOR_SYSTEM = """Ты — агент-ОРКЕСТРАТОР мультиагентной туристической системы.
Ты не выполняешь предметную работу сам. Твоя задача:
1. Понять запрос пользователя.
2. Выбрать подходящий навык (skill) из каталога ниже.
3. Написать КОНКРЕТНЫЙ системный промпт для агента-ИСПОЛНИТЕЛЯ: кто он,
   какую задачу решает, каким навыком руководствоваться (он его сам загрузит
   через load_skill), какие ограничения и в каком формате вернуть результат.
4. Сформулировать первое сообщение (task) исполнителю.

Отвечай СТРОГО одним JSON-объектом без пояснений и markdown-ограждений:
{
  "skill": "<skill_name из каталога>",
  "executor_system_prompt": "<системный промпт для исполнителя>",
  "task": "<конкретная задача исполнителю на естественном языке>"
}

Каталог навыков:
""" + load_skills_catalog()


class Orchestrator:
    def __init__(self):
        self.client: OpenAI = client
        self.model = MODEL_URI

    def plan(self, user_request: str) -> dict:
        """Просит модель-оркестратора вернуть план (skill + промпт исполнителя)."""
        logger.info("🧭 Оркестратор планирует: %s", _short_text(user_request, 120))
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM},
                {"role": "user", "content": user_request},
            ],
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            # запасной разбор: вырезаем первый {...}
            start, end = raw.find("{"), raw.rfind("}")
            plan = json.loads(raw[start : end + 1]) if start >= 0 else {}
        logger.info("🧭 План: skill=%s", plan.get("skill"))
        logger.debug("PLAN:\n%s", json.dumps(plan, ensure_ascii=False, indent=2))
        return plan

    def handle(self, user_request: str) -> str:
        """Полный цикл: план → запуск исполнителя → ответ."""
        plan = self.plan(user_request)
        skill = plan.get("skill")
        exec_prompt = plan.get("executor_system_prompt", "")
        task = plan.get("task", user_request)

        if not skill:
            return "❌ Оркестратор не смог выбрать навык. Уточните запрос."

        executor = spawn_executor(skill_name=skill, orchestrator_system_prompt=exec_prompt)
        logger.info("🚀 Запуск исполнителя '%s' по навыку '%s'", executor.name, skill)
        answer, _ = executor.run(task)

        u = executor.usage
        logger.info("📊 Исполнитель токенов: %s (p=%s c=%s)", u["total"], u["prompt"], u["completion"])
        return answer


def interactive():
    orch = Orchestrator()
    print("=" * 60)
    print("🧭 Мультиагентная система: ОРКЕСТРАТОР + исполнители")
    print("=" * 60)
    print("Введите 'exit' для выхода.\n")
    while True:
        q = input("👤 Вы: ").strip()
        if q.lower() in ("exit", "quit", "выход"):
            print("👋 До свидания!")
            break
        if not q:
            continue
        print(f"\n🤖 Ответ:\n{orch.handle(q)}\n")


if __name__ == "__main__":
    interactive()
