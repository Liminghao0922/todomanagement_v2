import json
import logging
from typing import Any

import azure.functions as func

from services.openai_service import extract_action_items_from_text

logger = logging.getLogger(__name__)


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(json.dumps(payload, ensure_ascii=False), mimetype="application/json", status_code=status_code)


def extract(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        meeting_text = (body.get("meeting_text") or "").strip()
        if not meeting_text:
            return _json_response({"error": "meeting_text is required"}, status_code=400)

        items = extract_action_items_from_text(meeting_text)
        return _json_response({"action_items": items, "count": len(items)})
    except Exception as exc:
        logger.exception("extract action items failed")
        return _json_response({"error": str(exc)}, status_code=500)
