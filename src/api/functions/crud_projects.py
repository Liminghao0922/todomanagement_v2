import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import azure.functions as func

from services.cosmos_service import get_projects_container

logger = logging.getLogger(__name__)


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(payload, ensure_ascii=False, default=str), mimetype="application/json", status_code=status_code)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_projects(req: func.HttpRequest, user_id: str) -> func.HttpResponse:
    try:
        container = get_projects_container()
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
        return _json_response(items)
    except Exception as exc:
        logger.exception("list_projects failed")
        return _json_response({"error": str(exc)}, status_code=500)


def get_project(req: func.HttpRequest, user_id: str, project_id: str) -> func.HttpResponse:
    try:
        project = _find_project_by_id(project_id, user_id)
        if not project:
            return _json_response({"error": "project not found"}, status_code=404)
        return _json_response(project)
    except Exception as exc:
        logger.exception("get_project failed")
        return _json_response({"error": str(exc)}, status_code=500)


def create_project(req: func.HttpRequest, user_id: str) -> func.HttpResponse:
    try:
        body = req.get_json()
        owner_id = (body.get("userId") or body.get("owner_id") or user_id or "").strip()
        name = (body.get("name") or "").strip()

        if not owner_id:
            return _json_response({"error": "userId is required"}, status_code=400)
        if not name:
            return _json_response({"error": "name is required"}, status_code=400)

        now = _now_iso()
        doc = {
            "id": str(uuid.uuid4()),
            "type": "project",
            "owner_id": owner_id,
            "name": name,
            "description": body.get("description"),
            "status": body.get("status", "active"),
            "priority": body.get("priority", "medium"),
            "startDate": body.get("startDate"),
            "endDate": body.get("endDate"),
            "created_at": now,
            "updated_at": now,
        }

        get_projects_container().create_item(doc)
        return _json_response(doc, status_code=201)
    except ValueError:
        return _json_response({"error": "invalid JSON body"}, status_code=400)
    except Exception as exc:
        logger.exception("create_project failed")
        return _json_response({"error": str(exc)}, status_code=500)


def update_project(req: func.HttpRequest, user_id: str, project_id: str) -> func.HttpResponse:
    try:
        body = req.get_json()
        existing = _find_project_by_id(project_id, user_id)
        if not existing:
            return _json_response({"error": "project not found"}, status_code=404)

        for key in ["name", "description", "status", "priority", "startDate", "endDate"]:
            if key in body:
                existing[key] = body[key]

        existing["updated_at"] = _now_iso()
        get_projects_container().replace_item(item=project_id, body=existing)
        return _json_response(existing)
    except ValueError:
        return _json_response({"error": "invalid JSON body"}, status_code=400)
    except Exception as exc:
        logger.exception("update_project failed")
        return _json_response({"error": str(exc)}, status_code=500)


def delete_project(req: func.HttpRequest, user_id: str, project_id: str) -> func.HttpResponse:
    try:
        existing = _find_project_by_id(project_id, user_id)
        if not existing:
            return _json_response({"error": "project not found"}, status_code=404)

        partition_key = existing.get("owner_id")
        if not partition_key:
            return _json_response({"error": "project owner_id is missing"}, status_code=500)

        get_projects_container().delete_item(item=project_id, partition_key=partition_key)
        return _json_response({"status": "deleted", "id": project_id})
    except Exception as exc:
        logger.exception("delete_project failed")
        return _json_response({"error": str(exc)}, status_code=500)


def _find_project_by_id(project_id: str, user_id: str | None = None) -> dict[str, Any] | None:
    container = get_projects_container()
    use_owner_scope = bool(user_id and user_id != "demo-user")

    if use_owner_scope:
        try:
            return container.read_item(item=project_id, partition_key=user_id)
        except Exception:
            pass

    query = "SELECT TOP 1 * FROM c WHERE c.id = @project_id"
    params: list[dict[str, object]] = [{"name": "@project_id", "value": project_id}]
    if use_owner_scope:
        query += " AND c.owner_id = @user_id"
        params.append({"name": "@user_id", "value": user_id})

    items = list(
        container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        )
    )
    return items[0] if items else None
