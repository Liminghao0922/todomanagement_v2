import json
import logging
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from time import perf_counter

import azure.functions as func

from services.cosmos_service import get_todos_container, get_projects_container
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
            try:
                query_vector = embed_text(search_text)
            except Exception as embed_exc:
                logger.warning("embed_text failed during list_todos search: %s", embed_exc)
                query_vector = None
            if query_vector:
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
        try:
            embedding = embed_text(content_text)
        except Exception as embed_exc:
            logger.warning("embed_text failed during create_todo: %s", embed_exc)
            embedding = None
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
            "embedding": embedding,
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
            try:
                existing["embedding"] = embed_text(content_text)
            except Exception as embed_exc:
                logger.warning("embed_text failed during update_todo: %s", embed_exc)

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


def generate_todos(req: func.HttpRequest, user_id: str) -> func.HttpResponse:
    try:
        count = int(req.params.get("count", "100"))
    except ValueError:
        return _json_response({"error": "count must be an integer"}, status_code=400)

    if count <= 0:
        return _json_response({"error": "count must be > 0"}, status_code=400)

    # Guardrail for local test endpoint to avoid accidental huge inserts.
    count = min(count, 5000)

    try:
        body = req.get_json()
        if not isinstance(body, dict):
            body = {}
    except ValueError:
        body = {}

    project_id = (body.get("projectId") or req.params.get("projectId") or "").strip() or None
    project_name = (body.get("projectName") or req.params.get("projectName") or "Current Project").strip()
    project_goal = (
        body.get("projectGoal")
        or req.params.get("projectGoal")
        or "Deliver measurable user and business impact"
    ).strip()

    # Auto-create a project if no projectId supplied.
    project_created = False
    if not project_id:
        now_pre = datetime.now(timezone.utc).isoformat()
        project_doc = {
            "id": str(uuid.uuid4()),
            "type": "project",
            "owner_id": user_id,
            "name": project_name,
            "description": project_goal,
            "status": "active",
            "priority": "high",
            "startDate": None,
            "endDate": None,
            "tags": ["generated"],
            "created_at": now_pre,
            "updated_at": now_pre,
        }
        try:
            get_projects_container().create_item(project_doc)
            project_id = project_doc["id"]
            project_created = True
            logger.info("auto-created project id=%s name=%s", project_id, project_name)
        except Exception:
            logger.exception("auto-create project failed, todos will have projectId=None")

    statuses = ["pending", "in-progress", "completed"]
    priorities = ["low", "medium", "high"]
    categories = ["work", "learning", "ops", "research", "delivery"]

    def generate_due_date(index: int) -> tuple[str, str]:
        today = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
        bucket = index % 4

        if bucket == 0:
            due = today - timedelta(days=random.randint(1, 7), hours=random.randint(0, 6))
            return due.isoformat(), "overdue"

        if bucket == 1:
            due = today.replace(hour=random.choice([10, 13, 16, 18]))
            return due.isoformat(), "today"

        if bucket == 2:
            due = today + timedelta(days=random.randint(1, 6), hours=random.choice([9, 12, 15]))
            return due.isoformat(), "this-week"

        due = today + timedelta(days=random.randint(7, 28), hours=random.choice([9, 11, 14]))
        return due.isoformat(), "this-month"

    high_impact_templates: list[dict[str, Any]] = [
        {
            "factor": "goal-metrics",
            "title": f"Define goals and success metrics for {project_name}",
            "description": "Create one-page objectives with measurable KPIs, baseline, and target outcomes.",
            "successMetric": "KPI sheet approved and baselined",
            "expectedOutcome": "Team aligned on impact targets",
            "estimatedHours": 4,
            "category": "strategy",
        },
        {
            "factor": "mvp-validation",
            "title": f"Build and validate MVP prototype for {project_name}",
            "description": "Deliver MVP flow and validate assumptions with pilot users.",
            "successMetric": "Pilot feedback completed and top issues ranked",
            "expectedOutcome": "Reduce feature risk early",
            "estimatedHours": 12,
            "category": "delivery",
        },
        {
            "factor": "user-research",
            "title": f"Run stakeholder and user interviews for {project_name}",
            "description": "Interview key users/stakeholders, summarize pain points, and convert to prioritized actions.",
            "successMetric": "At least 8 interviews synthesized",
            "expectedOutcome": "Backlog reflects validated user needs",
            "estimatedHours": 8,
            "category": "research",
        },
        {
            "factor": "quality-automation",
            "title": f"Set up automated testing and CI/CD for {project_name}",
            "description": "Implement core test suite and deployment pipeline with quality gates.",
            "successMetric": "CI pass rate >= 95% and deploy time reduced",
            "expectedOutcome": "Faster and safer release cadence",
            "estimatedHours": 10,
            "category": "ops",
        },
        {
            "factor": "adoption-plan",
            "title": f"Draft go-to-market and adoption plan for {project_name}",
            "description": "Prepare rollout plan, onboarding strategy, and support runbook.",
            "successMetric": "Launch checklist complete and owner assigned",
            "expectedOutcome": "Improve launch readiness and adoption",
            "estimatedHours": 6,
            "category": "growth",
        },
    ]

    started = perf_counter()
    created_count = 0
    seeded_high_impact = 0
    now = datetime.now(timezone.utc).isoformat()
    container = get_todos_container()

    # Seed guaranteed high-impact todos first, capped by requested count.
    for idx, template in enumerate(high_impact_templates[:count]):
        due_date, due_bucket = generate_due_date(idx)
        doc = {
            "id": str(uuid.uuid4()),
            "type": "todo",
            "owner_id": user_id,
            "title": template["title"],
            "description": template["description"],
            "status": "pending",
            "priority": "high",
            "dueDate": due_date,
            "projectId": project_id,
            "projectName": project_name,
            "projectGoal": project_goal,
            "category": template["category"],
            "complexity": random.choice(["medium", "complex"]),
            "estimatedHours": template["estimatedHours"],
            "actualHours": max(1, round(template["estimatedHours"] * random.uniform(0.7, 1.4), 1)),
            "tags": ["generated", "high-impact", template["factor"], due_bucket, f"seed-{idx + 1}"],
            "meetingId": None,
            "blockedBy": [],
            "precedes": [],
            "subtaskOf": [],
            "similarTo": [],
            "impactScore": random.randint(85, 98),
            "impactFactor": template["factor"],
            "isHighImpactCandidate": True,
            "successMetric": template["successMetric"],
            "expectedOutcome": template["expectedOutcome"],
            "created_at": now,
            "updated_at": now,
            # Test generation intentionally skips expensive embedding API calls.
            "embedding": [],
        }
        container.create_item(doc)
        created_count += 1
        seeded_high_impact += 1

    # Fill the remaining records with mixed-impact tasks that still carry impact metadata.
    for idx in range(created_count, count):
        status = random.choice(statuses)
        template = random.choice(high_impact_templates)
        is_high_impact = random.random() < 0.35
        due_date, due_bucket = generate_due_date(idx)

        estimated = random.choice([1, 2, 3, 5, 8])
        # Always populate a realistic actualHours so the data can be used to
        # estimate effort for new todos. Variance modeled as 0.6x - 1.6x of estimate.
        actual = max(1, round(estimated * random.uniform(0.6, 1.6), 1))

        doc = {
            "id": str(uuid.uuid4()),
            "type": "todo",
            "owner_id": user_id,
            "title": f"Generated Todo #{idx + 1}: {template['factor']}",
            "description": f"Auto-generated test todo item for {template['factor']} under {project_name}.",
            "status": status,
            "priority": "high" if is_high_impact else random.choice(priorities),
            "dueDate": due_date,
            "projectId": project_id,
            "projectName": project_name,
            "projectGoal": project_goal,
            "category": random.choice(categories),
            "complexity": random.choice(["simple", "medium", "complex"]),
            "estimatedHours": estimated,
            "actualHours": actual,
            "tags": ["generated", template["factor"], due_bucket, f"seed-{(idx % 10) + 1}"],
            "meetingId": None,
            "blockedBy": [],
            "precedes": [],
            "subtaskOf": [],
            "similarTo": [],
            "impactScore": random.randint(75, 99) if is_high_impact else random.randint(30, 80),
            "impactFactor": template["factor"],
            "isHighImpactCandidate": is_high_impact,
            "successMetric": template["successMetric"],
            "expectedOutcome": template["expectedOutcome"],
            "created_at": now,
            "updated_at": now,
            # Test generation intentionally skips expensive embedding API calls.
            "embedding": [],
        }
        container.create_item(doc)
        created_count += 1

    elapsed = round(perf_counter() - started, 3)
    return _json_response(
        {
            "createdCount": created_count,
            "timeSeconds": elapsed,
            "ownerId": user_id,
            "projectId": project_id,
            "projectName": project_name,
            "projectCreated": project_created,
            "seededHighImpact": seeded_high_impact,
        },
        status_code=201,
    )


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)
