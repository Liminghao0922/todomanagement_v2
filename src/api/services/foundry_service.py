import os
from typing import Any

import requests


def chat_with_foundry(user_id: str, message: str) -> dict[str, Any]:
    endpoint = os.getenv("FOUNDRY_AGENT_ENDPOINT", "").strip()
    api_key = os.getenv("FOUNDRY_AGENT_API_KEY", "").strip()

    if not endpoint:
        return {
            "error": "FOUNDRY_AGENT_ENDPOINT is not configured",
            "status": "not_configured",
        }

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "user_id": user_id,
        "message": message,
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    try:
        return response.json()
    except Exception:
        return {
            "answer": response.text,
            "raw": True,
        }
