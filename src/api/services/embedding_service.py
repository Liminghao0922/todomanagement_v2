import os
from typing import List

from openai import AzureOpenAI


def _client() -> AzureOpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    key = os.getenv("AZURE_OPENAI_KEY", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    if not endpoint or not key:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY are required")
    return AzureOpenAI(azure_endpoint=endpoint, api_key=key, api_version=api_version)


def embed_text(text: str) -> List[float]:
    model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
    response = _client().embeddings.create(model=model, input=text)
    return response.data[0].embedding
