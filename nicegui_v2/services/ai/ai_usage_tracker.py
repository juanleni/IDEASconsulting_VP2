from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


_USAGE_PATH = Path(__file__).resolve().parents[2] / "data" / "ai_usage_log.jsonl"


def log_ai_usage(*, model: str, prompt_kind: str, company_id: int | None, user_id: int | None, input_tokens: int = 0, output_tokens: int = 0) -> None:
    row = {
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "model": str(model or ""),
        "prompt_kind": str(prompt_kind or "general"),
        "company_id": int(company_id) if company_id else None,
        "user_id": int(user_id) if user_id else None,
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(input_tokens or 0) + int(output_tokens or 0),
    }
    _USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _USAGE_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
