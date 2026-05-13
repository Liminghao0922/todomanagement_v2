import json
import logging
from typing import Any

import azure.functions as func

from services.cosmos_service import get_todos_container
from services.embedding_service import embed_text

logger = logging.getLogger(__name__)


def _json_response(payload: Any, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(payload, ensure_ascii=False, default=str),
        mimetype="application/json",
        status_code=status_code,
    )


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = sum(a * a for a in v1) ** 0.5
    n2 = sum(b * b for b in v2) ** 0.5
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot / (n1 * n2)


def _keyword_score(query: str, candidate_text: str) -> float:
    """Lightweight word-overlap fallback when embeddings are unavailable."""
    if not query or not candidate_text:
        return 0.0
    q_words = {w.lower() for w in query.split() if len(w) > 2}
    c_words = {w.lower() for w in candidate_text.split() if len(w) > 2}
    if not q_words or not c_words:
        return 0.0
    return len(q_words & c_words) / len(q_words | c_words)


def estimate(req: func.HttpRequest, user_id: str) -> func.HttpResponse:
    try:
        body = req.get_json()
    except Exception:
        return _json_response({"error": "invalid JSON body"}, 400)

    title = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    category = (body.get("category") or "").strip()
    complexity = (body.get("complexity") or "").strip()

    if not title and not description:
        return _json_response({"error": "title or description is required"}, 400)

    query_text = f"{title}. {description}".strip()

    # Try semantic embedding first; fall back to keyword overlap if it fails.
    use_embedding = True
    query_vector: list[float] = []
    try:
        query_vector = embed_text(query_text)
    except Exception as exc:
        logger.warning("embed_text failed, falling back to keyword scoring: %s", exc)
        use_embedding = False

    container = get_todos_container()
    items = list(
        container.query_items(
            query=(
                "SELECT c.id, c.title, c.description, c.category, c.complexity, "
                "c.estimatedHours, c.actualHours, c.embedding, c.status "
                "FROM c WHERE c.owner_id = @uid AND IS_DEFINED(c.actualHours) "
                "AND NOT IS_NULL(c.actualHours)"
            ),
            parameters=[{"name": "@uid", "value": user_id}],
            enable_cross_partition_query=False,
        )
    )

    scored: list[dict] = []
    for it in items:
        actual = it.get("actualHours")
        if actual is None:
            continue
        try:
            actual_val = float(actual)
        except (TypeError, ValueError):
            continue
        if actual_val <= 0:
            continue

        if use_embedding and it.get("embedding"):
            score = _cosine_similarity(query_vector, it["embedding"])
        else:
            text = f"{it.get('title', '')} {it.get('description', '')}"
            score = _keyword_score(query_text, text)

        # Boost score when category/complexity match
        if category and it.get("category") == category:
            score += 0.05
        if complexity and it.get("complexity") == complexity:
            score += 0.05

        scored.append({
            "id": it.get("id"),
            "title": it.get("title"),
            "category": it.get("category"),
            "complexity": it.get("complexity"),
            "estimatedHours": it.get("estimatedHours"),
            "actualHours": actual_val,
            "similarity": round(score, 4),
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    # Keep meaningful matches only (similarity threshold)
    threshold = 0.15 if use_embedding else 0.05
    top = [s for s in scored if s["similarity"] >= threshold][:5]

    if not top:
        return _json_response({
            "found": False,
            "message": "No similar past todos with recorded actual hours were found.",
            "method": "embedding" if use_embedding else "keyword",
        })

    avg = round(sum(s["actualHours"] for s in top) / len(top), 1)
    min_h = round(min(s["actualHours"] for s in top), 1)
    max_h = round(max(s["actualHours"] for s in top), 1)

    reasoning_lines = [
        f"Found {len(top)} similar past todo(s) with recorded actual hours.",
        f"Average actual hours: {avg}h (range {min_h}h - {max_h}h).",
    ]
    if category:
        same_cat = sum(1 for s in top if s["category"] == category)
        if same_cat:
            reasoning_lines.append(f"{same_cat} of them share the same category ({category}).")
    if complexity:
        same_cx = sum(1 for s in top if s["complexity"] == complexity)
        if same_cx:
            reasoning_lines.append(f"{same_cx} of them share the same complexity ({complexity}).")

    return _json_response({
        "found": True,
        "estimatedHours": avg,
        "minHours": min_h,
        "maxHours": max_h,
        "sampleSize": len(top),
        "method": "embedding" if use_embedding else "keyword",
        "reasoning": " ".join(reasoning_lines),
        "similarTodos": top,
    })
