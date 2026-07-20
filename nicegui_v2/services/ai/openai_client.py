from __future__ import annotations

import os
from pathlib import Path

import httpx

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None


ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_env_file_openai_key() -> str:
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return ""
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = str(raw_line or "").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "OPENAI_API_KEY":
                return value.strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""


def resolve_openai_api_key() -> str:
    file_key = _read_env_file_openai_key()
    if file_key:
        os.environ["OPENAI_API_KEY"] = file_key
        return file_key
    return str(os.getenv("OPENAI_API_KEY", "")).strip()


def get_openai_client():
    key = resolve_openai_api_key()
    if OpenAI is None:
        raise RuntimeError("La libreria openai no esta instalada en el entorno.")
    if not key:
        raise RuntimeError("Falta configurar OPENAI_API_KEY.")
    if not key.startswith(("sk-", "sess-")):
        raise RuntimeError("OPENAI_API_KEY tiene formato invalido.")
    return OpenAI(api_key=key, http_client=httpx.Client(trust_env=False))
