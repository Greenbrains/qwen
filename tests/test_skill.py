import sys
from pathlib import Path

# Добавляем корень проекта в sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.builder import AsyncAgentBuilder

b = AsyncAgentBuilder()
meta, body = b._parse_skill("avia")
print("META:", meta)
print("BODY:", body[:200])