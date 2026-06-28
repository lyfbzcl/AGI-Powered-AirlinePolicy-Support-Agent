import os
from typing import Optional

from dotenv import load_dotenv


DEFAULT_DASHSCOPE_COMPAT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DEFAULT_DASHSCOPE_EMBEDDING_MODEL = "text-embedding-v4"
DEFAULT_DASHSCOPE_CHAT_MODEL = "qwen-plus"


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return default


def load_embedding_config() -> tuple[str, str, str]:
    """Load OpenAI-compatible embedding settings.

    Preferred for Alibaba Cloud Model Studio:
    DASHSCOPE_API_KEY plus optional EMBEDDING_BASE_URL and EMBEDDING_MODEL.
    """
    load_dotenv()

    api_key = _first_env("EMBEDDING_API_KEY", "DASHSCOPE_API_KEY")
    base_url = _first_env(
        "EMBEDDING_BASE_URL",
        "DASHSCOPE_BASE_URL",
        default=DEFAULT_DASHSCOPE_COMPAT_BASE_URL,
    )
    model = _first_env(
        "EMBEDDING_MODEL",
        default=DEFAULT_DASHSCOPE_EMBEDDING_MODEL,
    )

    if not api_key:
        raise ValueError("EMBEDDING_API_KEY or DASHSCOPE_API_KEY is missing in .env")
    if not base_url:
        raise ValueError("EMBEDDING_BASE_URL or DASHSCOPE_BASE_URL is missing in .env")
    if not model:
        raise ValueError("EMBEDDING_MODEL is missing in .env")

    return api_key, base_url, model


def load_chat_config() -> tuple[str, str, str]:
    """Load OpenAI-compatible chat settings."""
    load_dotenv()

    api_key = _first_env("LLM_API_KEY", "DASHSCOPE_API_KEY")
    base_url = _first_env(
        "LLM_BASE_URL",
        "DASHSCOPE_BASE_URL",
        default=DEFAULT_DASHSCOPE_COMPAT_BASE_URL,
    )
    model = _first_env(
        "LLM_CHAT_MODEL",
        default=DEFAULT_DASHSCOPE_CHAT_MODEL,
    )

    if not api_key:
        raise ValueError("LLM_API_KEY or DASHSCOPE_API_KEY is missing in .env")
    if not base_url:
        raise ValueError("LLM_BASE_URL or DASHSCOPE_BASE_URL is missing in .env")
    if not model:
        raise ValueError("LLM_CHAT_MODEL is missing in .env")

    return api_key, base_url, model


def load_top_k(default: int = 3) -> int:
    load_dotenv()
    raw_value = os.getenv("TOP_K", str(default)).strip()
    if not raw_value:
        raise ValueError("TOP_K is missing in .env")
    top_k = int(raw_value)
    if top_k <= 0:
        raise ValueError("TOP_K must be a positive integer")
    return top_k


def is_configured(*names: str) -> bool:
    load_dotenv()
    return bool(_first_env(*names))


def configured_model_name(*names: str, default: Optional[str] = None) -> str:
    load_dotenv()
    return _first_env(*names, default=default or "")
