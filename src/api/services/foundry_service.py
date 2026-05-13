import os
import importlib
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def _project_client(endpoint: str) -> Any:
    ai_projects_module = importlib.import_module("azure.ai.projects")
    identity_module = importlib.import_module("azure.identity")
    AIProjectClient = getattr(ai_projects_module, "AIProjectClient")
    DefaultAzureCredential = getattr(identity_module, "DefaultAzureCredential")

    return AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())


def chat_with_foundry(user_id: str, message: str, conversation_id: str | None = None) -> dict[str, Any]:
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT", "").strip() or os.getenv("FOUNDRY_AGENT_ENDPOINT", "").strip()
    agent_name = os.getenv("FOUNDRY_AGENT_NAME", "todomanagement-agent").strip()
    agent_version = os.getenv("FOUNDRY_AGENT_VERSION", "1").strip()

    if not endpoint:
        return {
            "error": "FOUNDRY_PROJECT_ENDPOINT is not configured",
            "status": "not_configured",
        }

    try:
        project_client = _project_client(endpoint)
        openai_client = project_client.get_openai_client()

        # Create a new server-side conversation on the first turn
        if not conversation_id:
            conversation = openai_client.conversations.create()
            conversation_id = conversation.id

        response = openai_client.responses.create(
            input=f"[user_id={user_id}] {message}",
            conversation=conversation_id,
            extra_body={
                "agent_reference": {
                    "name": agent_name,
                    "version": agent_version,
                    "type": "agent_reference",
                }
            },
        )

        return {
            "answer": response.output_text or "",
            "conversationId": conversation_id,
            "status": "ok",
        }
    except Exception as exc:
        return {
            "error": f"Foundry SDK request failed: {str(exc)}",
            "status": "upstream_error",
        }
