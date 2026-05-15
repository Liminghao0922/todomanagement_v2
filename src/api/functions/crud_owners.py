import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import azure.functions as func

from services.cosmos_service import get_owners_container

logger = logging.getLogger(__name__)


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(payload, ensure_ascii=False, default=str), mimetype="application/json", status_code=status_code)


def create_owner(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        return _json_response({"error": "invalid JSON body"}, status_code=400)

    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    owner_id = (body.get("id") or "").strip() or str(uuid.uuid4())

    if not name:
        return _json_response({"error": "name is required"}, status_code=400)
    if not email:
        return _json_response({"error": "email is required"}, status_code=400)

    # Get container outside try block to ensure it's always defined
    try:
        container = get_owners_container()
    except RuntimeError as exc:
        return _json_response({"error": str(exc)}, status_code=503)
    except Exception as exc:
        logger.exception("get_owners_container failed")
        return _json_response({"error": str(exc)}, status_code=503)

    # Check if owner already exists
    try:
        existing = container.read_item(item=owner_id, partition_key=owner_id)
        return _json_response(existing, status_code=200)
    except RuntimeError as exc:
        return _json_response({"error": str(exc)}, status_code=503)
    except Exception:
        # Not found or read issue; continue to create path.
        pass

    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": owner_id,
        "name": name,
        "email": email,
        "created_at": now,
        "updated_at": now,
    }

    try:
        container.create_item(doc)
        return _json_response(doc, status_code=201)
    except Exception as exc:
        logger.exception("create_owner failed")
        return _json_response({"error": str(exc)}, status_code=500)
