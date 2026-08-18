"""
usage.py — Централизованный учёт токенов мультиагентной системы.

Возвращает то, что было сильной стороной одиночного агента: видно,
сколько токенов «съел» каждый агент и вся сессия целиком.
Потокобезопасно не требуется — asyncio однопоточный.
"""
from __future__ import annotations
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger("agent.usage")


@dataclass
class _Counter:
    prompt: int = 0
    completion: int = 0
    total: int = 0
    calls: int = 0

    def add(self, prompt: int, completion: int, total: int) -> None:
        self.prompt += prompt
        self.completion += completion
        self.total += total
        self.calls += 1


class UsageTracker:
    """Копит статистику токенов по агентам и по сессии в целом."""

    def __init__(self) -> None:
        self.session = _Counter()
        self.by_agent: Dict[str, _Counter] = defaultdict(_Counter)

    def record(self, agent: str, usage) -> None:
        """Регистрирует usage из ответа LLM. `usage` — объект OpenAI или None."""
        if not usage:
            return
        p = getattr(usage, "prompt_tokens", 0) or 0
        c = getattr(usage, "completion_tokens", 0) or 0
        t = getattr(usage, "total_tokens", 0) or (p + c)
        self.session.add(p, c, t)
        self.by_agent[agent].add(p, c, t)
        logger.debug(
            "TOKENS [%s] prompt=%d completion=%d total=%d (session_total=%d)",
            agent, p, c, t, self.session.total,
        )

    def turn_line(self, agent: str) -> str:
        """Короткая строка по последнему агенту — для консоли после каждого хода."""
        a = self.by_agent[agent]
        return (
            f"🎫 Токены [{agent}]: +{a.total} за агента | "
            f"сессия: {self.session.total} (in {self.session.prompt} / out {self.session.completion})"
        )

    def report(self) -> str:
        """Итоговый отчёт по сессии — печатается при выходе."""
        lines = [
            "═" * 52,
            "📊 ИТОГО ПО ТОКЕНАМ ЗА СЕССИЮ",
            "═" * 52,
            f"{'Агент':<18}{'вызовы':>8}{'in':>10}{'out':>10}{'всего':>10}",
            "-" * 52,
        ]
        for name, c in sorted(self.by_agent.items(), key=lambda x: -x[1].total):
            lines.append(f"{name:<18}{c.calls:>8}{c.prompt:>10}{c.completion:>10}{c.total:>10}")
        s = self.session
        lines.append("-" * 52)
        lines.append(f"{'ВСЕГО':<18}{s.calls:>8}{s.prompt:>10}{s.completion:>10}{s.total:>10}")
        lines.append("═" * 52)
        return "\n".join(lines)