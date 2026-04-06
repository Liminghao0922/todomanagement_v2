import os
from typing import Any

from gremlin_python.driver import client
from gremlin_python.driver.serializer import GraphSONSerializersV2d0


def upsert_todo_vertex(todo_doc: dict[str, Any]) -> None:
    graph_client = _get_client()
    if not graph_client:
        return

    owner_id = (todo_doc.get("owner_id") or "").strip()
    todo_id = (todo_doc.get("id") or "").strip()
    if not owner_id or not todo_id:
        return

    title = (todo_doc.get("title") or "").replace("'", "\\'")
    status = (todo_doc.get("status") or "pending").replace("'", "\\'")
    priority = (todo_doc.get("priority") or "medium").replace("'", "\\'")

    script = (
        "g.V().has('todo','id',todoId).fold()"
        ".coalesce(unfold(), addV('todo').property('id', todoId).property('owner_id', ownerId))"
        ".property('title', title).property('status', status).property('priority', priority)"
    )
    params = {
        "todoId": todo_id,
        "ownerId": owner_id,
        "title": title,
        "status": status,
        "priority": priority,
    }
    graph_client.submit(script, params).all().result()

    _upsert_edges(graph_client, owner_id, todo_id, "BLOCKED_BY", todo_doc.get("blockedBy") or [])
    _upsert_edges(graph_client, owner_id, todo_id, "PRECEDES", todo_doc.get("precedes") or [])
    _upsert_edges(graph_client, owner_id, todo_id, "SUBTASK_OF", todo_doc.get("subtaskOf") or [])
    _upsert_edges(graph_client, owner_id, todo_id, "SIMILAR_TO", todo_doc.get("similarTo") or [])


def query_related(owner_id: str, todo_id: str, relation: str = "SIMILAR_TO") -> list[dict[str, Any]]:
    graph_client = _get_client()
    if not graph_client:
        return []

    script = (
        "g.V().has('todo','id',todoId).has('owner_id', ownerId)"
        ".outE(relation).inV().project('id','title','status','priority')"
        ".by(values('id')).by(values('title')).by(values('status')).by(values('priority'))"
    )
    params = {
        "todoId": todo_id,
        "ownerId": owner_id,
        "relation": relation,
    }
    return graph_client.submit(script, params).all().result()


def _upsert_edges(graph_client: client.Client, owner_id: str, source_id: str, edge_label: str, targets: list[str]) -> None:
    for target_id in targets:
        if not target_id:
            continue
        script = (
            "g.V().has('todo','id',sourceId).has('owner_id', ownerId).as('s')"
            ".V().has('todo','id',targetId).has('owner_id', ownerId).fold()"
            ".coalesce(unfold(), addV('todo').property('id', targetId).property('owner_id', ownerId))"
            ".as('t').select('s').coalesce(outE(edgeLabel).where(inV().as('t')), addE(edgeLabel).to('t'))"
        )
        params = {
            "sourceId": source_id,
            "targetId": target_id,
            "ownerId": owner_id,
            "edgeLabel": edge_label,
        }
        graph_client.submit(script, params).all().result()


def _get_client() -> client.Client | None:
    endpoint = os.getenv("COSMOS_GREMLIN_ENDPOINT", "").strip()
    database = os.getenv("COSMOS_GREMLIN_DATABASE", "todo-graph-db").strip()
    graph = os.getenv("COSMOS_GREMLIN_GRAPH", "todo-graph").strip()
    key = os.getenv("COSMOS_KEY", "").strip()
    if not endpoint or not key:
        return None

    if endpoint.startswith("wss://"):
        ws_endpoint = endpoint
    else:
        ws_endpoint = endpoint.replace("https://", "wss://").rstrip("/") + "/"

    return client.Client(
        url=ws_endpoint,
        traversal_source="g",
        username=f"/dbs/{database}/colls/{graph}",
        password=key,
        message_serializer=GraphSONSerializersV2d0(),
    )
