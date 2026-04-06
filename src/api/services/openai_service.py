import json
import os
from typing import List, Dict

from openai import AzureOpenAI


def _client() -> AzureOpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    key = os.getenv("AZURE_OPENAI_KEY", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if not endpoint or not key:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY are required")
    return AzureOpenAI(azure_endpoint=endpoint, api_key=key, api_version=api_version)


def extract_action_items_from_text(meeting_text: str) -> List[Dict[str, str]]:
    model = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4o-mini")
    prompt = (
        "Extract action items from meeting text. "
        "Return strict JSON array with fields: title, priority(low|medium|high), owner(optional)."
    )

    completion = _client().chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": meeting_text},
        ],
    )
    content = completion.choices[0].message.content or "[]"

    try:
        start = content.find("[")
        end = content.rfind("]")
        if start >= 0 and end >= 0:
            return json.loads(content[start : end + 1])
        return json.loads(content)
    except Exception:
        return []
