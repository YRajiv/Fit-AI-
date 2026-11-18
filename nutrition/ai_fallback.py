
import logging
import time
import requests

from django.conf import settings
from typing import Any

from google.genai import types

logger = logging.getLogger(__name__)


# ============================================================
# GEMINI API
# ============================================================

def call_gemini(
    client,
    model_name: str,
    contents: list,
    timeout: int = 30
) -> Any:
    """
    Call Gemini.

    JSON mode is preserved because nutrition APIs
    may require structured JSON responses.
    """

    if client is None:
        raise RuntimeError("Gemini client is unavailable")

    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    if not response.text or not response.text.strip():
        raise ValueError("Gemini returned an empty response")

    return response


# ============================================================
# GROQ API
# ============================================================

def call_groq(
    messages: list,
    model: str = "llama-3.3-70b-versatile",
    timeout: int = 30
) -> dict:
    """
    Call Groq API using HTTP requests.
    """

    api_key = getattr(
        settings,
        "GROQ_API_KEY",
        None
    )

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured"
        )

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=timeout,
    )

    response.raise_for_status()

    result = response.json()

    # Validate response
    choices = result.get("choices", [])

    if not choices:
        raise ValueError("Groq returned no choices")

    answer = (
        choices[0]
        .get("message", {})
        .get("content", "")
    )

    if not answer or not answer.strip():
        raise ValueError("Groq returned empty content")

    return result


# ============================================================
# OPENAI API
# ============================================================

def call_openai(
    messages: list,
    model: str = "gpt-4o-mini",
    timeout: int = 30
) -> Any:
    """
    Call OpenAI API.
    """

    api_key = getattr(
        settings,
        "OPENAI_API_KEY",
        None
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured"
        )

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        timeout=timeout,
    )

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )

    # Validate response
    if not response.choices:
        raise ValueError("OpenAI returned no choices")

    answer = response.choices[0].message.content

    if not answer or not answer.strip():
        raise ValueError("OpenAI returned empty content")

    return response


# ============================================================
# FALLBACK SYSTEM
# ============================================================

def fallback_chain(steps):
    """
    Try providers in order.

    Example:
        Gemini -> Groq -> OpenAI

    If a provider fails or returns empty content,
    try the next provider.
    """

    last_error = None

    for name, fn in steps:

        start = time.time()

        try:

            logger.info(
                "Trying AI provider: %s",
                name
            )

            response = fn()

            # --------------------------------------------
            # Validate empty response
            # --------------------------------------------

            if response is None:
                raise ValueError(
                    "Provider returned None"
                )

            if isinstance(response, str):

                if not response.strip():
                    raise ValueError(
                        "Provider returned empty text"
                    )

            # --------------------------------------------
            # Validate dictionary responses
            # --------------------------------------------

            if isinstance(response, dict):

                choices = response.get(
                    "choices",
                    []
                )

                if not choices:
                    raise ValueError(
                        "Provider returned no choices"
                    )

                content = (
                    choices[0]
                    .get("message", {})
                    .get("content", "")
                )

                if not content or not content.strip():
                    raise ValueError(
                        "Provider returned empty content"
                    )

            # --------------------------------------------
            # Success
            # --------------------------------------------

            elapsed = time.time() - start

            logger.info(
                "Provider %s succeeded in %.2f seconds",
                name,
                elapsed
            )

            return response, name

        except Exception as exc:

            elapsed = time.time() - start

            logger.exception(
                "Provider %s failed after %.2f seconds",
                name,
                elapsed
            )

            last_error = exc

            # Try the next provider
            continue

    # --------------------------------------------
    # All providers failed
    # --------------------------------------------

    raise RuntimeError(
        f"All AI providers failed. "
        f"Last error: {last_error}"
    )
