from __future__ import annotations

import logging

from groq import Groq

from src.common.config import AppConfig, load_config

logger = logging.getLogger(__name__)


def create_groq_client(config: AppConfig | None = None) -> Groq:
    cfg = config or load_config()
    if not cfg.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your environment or .env file for Phase 4."
        )
    return Groq(api_key=cfg.groq_api_key)


def groq_chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.35,
    max_tokens: int = 2048,
    config: AppConfig | None = None,
) -> str:
    cfg = config or load_config()
    client = create_groq_client(cfg)
    resolved_model = model or cfg.groq_model
    logger.info("Groq chat completion model=%s messages=%s", resolved_model, len(messages))
    response = client.chat.completions.create(
        model=resolved_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    choice = response.choices[0].message
    content = choice.content if choice else None
    if not content:
        raise RuntimeError("Groq returned empty message content")
    return content.strip()
