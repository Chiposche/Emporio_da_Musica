"""
Logging estruturado de turnos do agente em JSONL.
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "logs" / "agent.jsonl"


def _write_entry(entry: dict):
    LOG_PATH.parent.mkdir(exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_turn(
    session_id: str,
    user_message: str,
    thoughts: list[dict],
    timing: dict,
    response: str,
):
    tools_called = []
    for t in thoughts:
        if t.get("tool") and t["tool"] != "_timing":
            tools_called.append({"name": t["tool"], "args": t.get("args", {})})

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_message": user_message[:500],
        "tools_called": tools_called,
        "provider": timing.get("modelo", ""),
        "ttft_ms": timing.get("ttft_ms"),
        "total_ms": timing.get("total_ms"),
        "tool_rounds": timing.get("rodadas_de_ferramenta"),
        "fallbacks": timing.get("fallbacks", []),
        "response_length": len(response),
        "tokens": {
            "prompt": timing.get("prompt_tokens"),
            "completion": timing.get("completion_tokens"),
            "total": timing.get("total_tokens"),
        },
    }

    threading.Thread(target=_write_entry, args=(entry,), daemon=True).start()
