import logging
import uuid
from datetime import datetime, timedelta, timezone

import azure.functions as func

from services.calendar_service import get_recent_calendar_items
from services.cosmos_service import get_owners_container, get_todos_container
from services.embedding_service import embed_text
from services.openai_service import extract_action_items_from_text

logger = logging.getLogger(__name__)


def auto_scan_calendar_timer(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logger.info("calendar timer was past due")

    owners = list(get_owners_container().query_items("SELECT c.id, c.email FROM c", enable_cross_partition_query=True))
    for owner in owners:
        owner_id = owner.get("id")
        if owner_id:
            principal = owner.get("email") or owner_id
            _scan_user(owner_id, principal)


def _scan_user(owner_id: str, owner_principal: str) -> None:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=24)
    end = now + timedelta(hours=48)
    meetings = get_recent_calendar_items(owner_principal, start, end)
    todos_container = get_todos_container()

    for meeting in meetings:
        text = (meeting.get("bodyPreview") or "").strip()
        if not text:
            continue

        action_items = extract_action_items_from_text(text)
        for item in action_items:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            dedupe_query = "SELECT TOP 1 c.id FROM c WHERE c.owner_id = @owner_id AND c.meetingId = @meeting_id AND c.title = @title"
            dedupe = list(
                todos_container.query_items(
                    dedupe_query,
                    parameters=[
                        {"name": "@owner_id", "value": owner_id},
                        {"name": "@meeting_id", "value": meeting.get("id")},
                        {"name": "@title", "value": title},
                    ],
                    enable_cross_partition_query=False,
                )
            )
            if dedupe:
                continue

            now_iso = datetime.now(timezone.utc).isoformat()
            doc = {
                "id": str(uuid.uuid4()),
                "type": "todo",
                "owner_id": owner_id,
                "title": title,
                "description": f"Auto-created from meeting: {meeting.get('subject', 'Untitled meeting')}",
                "status": "pending",
                "priority": item.get("priority", "medium"),
                "category": "meeting-follow-up",
                "meetingId": meeting.get("id"),
                "tags": ["auto", "calendar"],
                "created_at": now_iso,
                "updated_at": now_iso,
                "embedding": embed_text(title),
            }
            todos_container.create_item(doc)
            logger.info("created auto todo for owner=%s meeting=%s", owner_id, meeting.get("id"))
