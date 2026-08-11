import os
from typing import List

from services.foundry_service import _auth_headers, _post_json


def embed_text(text: str) -> List[float]:
    endpoint = (
        os.getenv("FOUNDRY_PROJECT_ENDPOINT", "").strip()
        or os.getenv("FOUNDRY_AGENT_ENDPOINT", "").strip()
    )
    if not endpoint:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT is required")

    model = os.getenv("FOUNDRY_EMBEDDING_DEPLOYMENT", "text-embedding-3-small").strip()
    url = endpoint.rstrip("/") + "/openai/v1/embeddings"
    payload = {
        "model": model,
        "input": text,
    }
    response = _post_json(url, payload, _auth_headers())
    data = response.get("data", [])
    if not data:
        raise RuntimeError("Foundry embeddings response missing data")
    embedding = data[0].get("embedding")
    if not isinstance(embedding, list):
        raise RuntimeError("Foundry embeddings response missing embedding vector")
    return embedding
