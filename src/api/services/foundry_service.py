import os
import importlib
import json
from urllib.error import HTTPError
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Any


def _token_from_managed_identity(resource: str = "https://cognitiveservices.azure.com/") -> str:
    identity_endpoint = os.getenv("IDENTITY_ENDPOINT", "")
    identity_header = os.getenv("IDENTITY_HEADER", "")
    client_id = os.getenv("FOUNDRY_MANAGED_IDENTITY_CLIENT_ID", "").strip()

    if identity_endpoint and identity_header:
        query = {"api-version": "2019-08-01", "resource": resource}
        if client_id:
            query["client_id"] = client_id
        url = identity_endpoint + ("&" if "?" in identity_endpoint else "?") + urllib.parse.urlencode(query)
        request = urllib.request.Request(
            url,
            headers={"X-IDENTITY-HEADER": identity_header, "Metadata": "true"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            token = json.loads(response.read().decode("utf-8")).get("access_token", "")
            if token:
                return token

    raise RuntimeError("Managed identity token acquisition returned no access_token")


def _auth_headers() -> dict[str, str]:
    api_key = os.getenv("FOUNDRY_AGENT_API_KEY", "").strip() or os.getenv("AZURE_OPENAI_KEY", "").strip()
    if api_key:
        return {"api-key": api_key, "Content-Type": "application/json"}
    return {
        "Authorization": f"Bearer {_token_from_managed_identity()}",
        "Content-Type": "application/json",
    }


def _post_json(url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP Error {exc.code}: {detail}") from exc


@lru_cache(maxsize=1)
def _project_client(endpoint: str) -> Any:
    ai_projects_module = importlib.import_module("azure.ai.projects")
    identity_module = importlib.import_module("azure.identity")
    AIProjectClient = getattr(ai_projects_module, "AIProjectClient")
    DefaultAzureCredential = getattr(identity_module, "DefaultAzureCredential")

    return AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential(), allow_preview=True)


def chat_with_foundry(user_id: str, message: str, conversation_id: str | None = None) -> dict[str, Any]:
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "").strip() or os.getenv("FOUNDRY_AGENT_ENDPOINT", "").strip()
    agent_name = os.getenv("FOUNDRY_AGENT_NAME", "todomanagement-agent").strip()
    model = os.getenv("FOUNDRY_AGENT_MODEL", "gpt-5.4-mini").strip()

    if not endpoint:
        return {
            "error": "FOUNDRY_PROJECT_ENDPOINT is not configured",
            "status": "not_configured",
        }

    try:
        project_client = _project_client(endpoint)
        openai_client = project_client.get_openai_client(agent_name=agent_name)

        request: dict[str, Any] = {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": f"[user_id={user_id}] {message}",
                }
            ],
        }
        if conversation_id and conversation_id.startswith("resp_"):
            request["previous_response_id"] = conversation_id

        response = openai_client.responses.create(**request)

        return {
            "answer": response.output_text or "",
            "conversationId": response.id,
            "status": "ok",
        }
    except Exception as exc:
        return {
            "error": f"Foundry SDK request failed: {exc}",
            "status": "upstream_error",
        }
