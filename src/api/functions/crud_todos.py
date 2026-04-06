import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import azure.functions as func

from services.cosmos_service import get_todos_container
from services.embedding_service import embed_text
from services.graph_service import upsert_todo_vertex

logger = logging.getLogger(__name__)


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(payload, ensure_ascii=False, default=str), mimetype="application/json", status_code=status_code)


def list_todos(req: func.HttpRequest, user_id: str) -> func.HttpResponse:
    try:
        container = get_todos_container()
        page_size = int(req.params.get("pageSize", "20"))
        offset = int(req.params.get("offset", "0"))
        status = req.params.get("status")
        query = "SELECT * FROM c WHERE c.owner_id = @user_id"
        params: list[dict[str, object]] = [{"name": "@user_id", "value": user_id}]
        if status:
            query += " AND c.status = @status"
            params.append({"name": "@status", "value": status})
        query += " ORDER BY c.created_at DESC"

        items = list(
            container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=False,
            )
        )

        search_text = req.params.get("search")
        if search_text:
            # Fallback semantic ranking in app layer when vector ORDER BY is unavailable.
            query_vector = embed_text(search_text)
            for item in items:
                item_vector = item.get("embedding") or []
                score = _cosine_similarity(query_vector, item_vector)
                item["_semanticScore"] = score
            items = sorted(items, key=lambda x: x.get("_semanticScore", 0.0), reverse=True)

        sliced = items[offset : offset + page_size]
        next_offset = offset + page_size if offset + page_size < len(items) else None
        return _json_response(
            {
                "items": sliced,
                "total": len(items),
                "offset": offset,
                "pageSize": page_size,
                "nextOffset": next_offset,
            }
        )
    except Exception as exc:
        logger.exception("list_todos failed")
        return _json_response({"error": str(exc)}, status_code=500)


def create_todo(req: func.HttpRequest, user_id: str) -> func.HttpResponse:
    try:
        body = req.get_json()
        now = datetime.now(timezone.utc).isoformat()
        content_text = f"{body.get('title', '')}\n{body.get('description', '')}"
        doc = {
            "id": str(uuid.uuid4()),
            "type": "todo",
            "owner_id": user_id,
            "title": body.get("title", "").strip(),
            "description": body.get("description"),
            "status": body.get("status", "pending"),
            "priority": body.get("priority", "medium"),
            "dueDate": body.get("dueDate"),
            "projectId": body.get("projectId"),
            "category": body.get("category"),
            "complexity": body.get("complexity"),
            "estimatedHours": body.get("estimatedHours"),
            "actualHours": body.get("actualHours"),
            "tags": body.get("tags") or [],
            "meetingId": body.get("meetingId"),
            "blockedBy": body.get("blockedBy") or [],
            "precedes": body.get("precedes") or [],
            "subtaskOf": body.get("subtaskOf") or [],
            "similarTo": body.get("similarTo") or [],
            "created_at": now,
            "updated_at": now,
            "embedding": embed_text(content_text),
        }

        if not doc["title"]:
            return _json_response({"error": "title is required"}, status_code=400)

        get_todos_container().create_item(doc)
        upsert_todo_vertex(doc)
        return _json_response(doc, status_code=201)
    except Exception as exc:
        logger.exception("create_todo failed")
        return _json_response({"error": str(exc)}, status_code=500)


def update_todo(req: func.HttpRequest, user_id: str, todo_id: str) -> func.HttpResponse:
    try:
        container = get_todos_container()
        existing = container.read_item(item=todo_id, partition_key=user_id)
        body = req.get_json()

        for key in [
            "title",
            "description",
            "status",
            "priority",
            "dueDate",
            "projectId",
            "category",
            "complexity",
            "estimatedHours",
            "actualHours",
            "tags",
            "meetingId",
            "blockedBy",
            "precedes",
            "subtaskOf",
            "similarTo",
        ]:
            if key in body:
                existing[key] = body[key]

        if "title" in body or "description" in body:
            content_text = f"{existing.get('title', '')}\n{existing.get('description', '')}"
            existing["embedding"] = embed_text(content_text)

        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        container.replace_item(item=todo_id, body=existing)
        upsert_todo_vertex(existing)
        return _json_response(existing)
    except Exception as exc:
        logger.exception("update_todo failed")
        return _json_response({"error": str(exc)}, status_code=500)


def delete_todo(user_id: str, todo_id: str) -> func.HttpResponse:
    try:
        get_todos_container().delete_item(item=todo_id, partition_key=user_id)
        return _json_response({"status": "deleted", "id": todo_id})
    except Exception as exc:
        logger.exception("delete_todo failed")
        return _json_response({"error": str(exc)}, status_code=500)


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)
