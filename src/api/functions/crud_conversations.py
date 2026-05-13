import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import azure.functions as func

from services.cosmos_service import get_conversations_container

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False, default=str),
        mimetype="application/json",
        status_code=status_code,
    )


def list_conversations(user_id: str) -> func.HttpResponse:
    try:
        container = get_conversations_container()
        items = list(
            container.query_items(
                query="SELECT c.id, c.owner_id, c.title, c.conversationId, c.createdAt, c.updatedAt FROM c WHERE c.owner_id = @uid ORDER BY c.updatedAt DESC",
                parameters=[{"name": "@uid", "value": user_id}],
                enable_cross_partition_query=False,
            )
        )
        return _json_response({"items": items})
    except Exception as exc:
        logger.exception("list_conversations failed")
        return _json_response({"error": str(exc)}, 500)


def get_conversation(user_id: str, conversation_doc_id: str) -> func.HttpResponse:
    try:
        container = get_conversations_container()
        doc = container.read_item(item=conversation_doc_id, partition_key=user_id)
        return _json_response(doc)
    except Exception as exc:
        logger.exception("get_conversation failed")
        return _json_response({"error": str(exc)}, 404)


def delete_conversation(user_id: str, conversation_doc_id: str) -> func.HttpResponse:
    try:
        container = get_conversations_container()
        container.delete_item(item=conversation_doc_id, partition_key=user_id)
        return _json_response({"deleted": True})
    except Exception as exc:
        logger.exception("delete_conversation failed")
        return _json_response({"error": str(exc)}, 500)


def upsert_conversation(
    user_id: str,
    conversation_id: str,
    user_message: str,
    assistant_message: str,
    doc_id: str | None = None,
) -> dict:
    """
    Save or update a conversation document in Cosmos DB.
    Returns the updated document (with id for subsequent calls).
    """
    container = get_conversations_container()
    now = _now()

    if doc_id:
        # Load and append messages to existing document
        try:
            doc = container.read_item(item=doc_id, partition_key=user_id)
        except Exception:
            doc = None

        if doc:
            doc["messages"].append({"role": "user", "content": user_message, "timestamp": now})
            doc["messages"].append({"role": "assistant", "content": assistant_message, "timestamp": now})
            doc["updatedAt"] = now
            container.upsert_item(doc)
            return {"id": doc["id"], "conversationId": doc["conversationId"]}

    # Create new conversation document
    title = user_message[:60] + ("…" if len(user_message) > 60 else "")
    new_doc = {
        "id": str(uuid.uuid4()),
        "owner_id": user_id,
        "conversationId": conversation_id,
        "title": title,
        "messages": [
            {"role": "user", "content": user_message, "timestamp": now},
            {"role": "assistant", "content": assistant_message, "timestamp": now},
        ],
        "createdAt": now,
        "updatedAt": now,
    }
    container.upsert_item(new_doc)
    return {"id": new_doc["id"], "conversationId": new_doc["conversationId"]}
