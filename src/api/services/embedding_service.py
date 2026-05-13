import os
from typing import List

from services.foundry_service import _project_client


def embed_text(text: str) -> List[float]:
    endpoint = (
        os.getenv("FOUNDRY_PROJECT_ENDPOINT", "").strip()
        or os.getenv("FOUNDRY_AGENT_ENDPOINT", "").strip()
    )
    if not endpoint:
        raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT is required")

    model = os.getenv("FOUNDRY_EMBEDDING_DEPLOYMENT", "text-embedding-3-small").strip()
    openai_client = _project_client(endpoint).get_openai_client()
    response = openai_client.embeddings.create(model=model, input=text)
    return response.data[0].embedding
