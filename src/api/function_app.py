import json
import logging
from datetime import datetime, timezone

import azure.functions as func

from functions import crud_owners, crud_projects, crud_todos, crud_conversations, estimate_hours
from services.foundry_service import chat_with_foundry
from services.graph_service import query_related

logger = logging.getLogger(__name__)
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _resolve_user_id(req: func.HttpRequest) -> str:
    # Use header/query first, then JSON body to support calls that send userId in payload.
    header_or_query = req.headers.get("x-user-id") or req.params.get("userId")
    if header_or_query:
        return header_or_query

    try:
        body = req.get_json()
        if isinstance(body, dict):
            body_user_id = (body.get("userId") or body.get("owner_id") or "").strip()
            if body_user_id:
                return body_user_id
    except Exception:
        pass

    return "demo-user"


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(
            {
                "status": "healthy",
                "service": "Todo Management Functions API",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ),
        mimetype="application/json",
    )


@app.route(route="todos", methods=["GET"])
def list_todos(req: func.HttpRequest) -> func.HttpResponse:
    return crud_todos.list_todos(req, _resolve_user_id(req))


@app.route(route="todos", methods=["POST"])
def create_todo(req: func.HttpRequest) -> func.HttpResponse:
    return crud_todos.create_todo(req, _resolve_user_id(req))


@app.route(route="generate-todos", methods=["POST"])
def generate_todos(req: func.HttpRequest) -> func.HttpResponse:
    return crud_todos.generate_todos(req, _resolve_user_id(req))


@app.route(route="owners", methods=["POST"])
def create_owner(req: func.HttpRequest) -> func.HttpResponse:
    return crud_owners.create_owner(req)


@app.route(route="projects", methods=["GET"])
def list_projects(req: func.HttpRequest) -> func.HttpResponse:
    return crud_projects.list_projects(req, _resolve_user_id(req))


@app.route(route="projects", methods=["POST"])
def create_project(req: func.HttpRequest) -> func.HttpResponse:
    return crud_projects.create_project(req, _resolve_user_id(req))


@app.route(route="projects/{project_id}", methods=["GET"])
def get_project(req: func.HttpRequest) -> func.HttpResponse:
    project_id = req.route_params.get("project_id", "")
    return crud_projects.get_project(req, _resolve_user_id(req), project_id)


@app.route(route="projects/{project_id}", methods=["PATCH"])
def update_project(req: func.HttpRequest) -> func.HttpResponse:
    project_id = req.route_params.get("project_id", "")
    return crud_projects.update_project(req, _resolve_user_id(req), project_id)


@app.route(route="projects/{project_id}", methods=["DELETE"])
def delete_project(req: func.HttpRequest) -> func.HttpResponse:
    project_id = req.route_params.get("project_id", "")
    return crud_projects.delete_project(req, _resolve_user_id(req), project_id)


@app.route(route="todos/{todo_id}", methods=["PATCH"])
def update_todo(req: func.HttpRequest) -> func.HttpResponse:
    todo_id = req.route_params.get("todo_id", "")
    return crud_todos.update_todo(req, _resolve_user_id(req), todo_id)


@app.route(route="todos/{todo_id}", methods=["DELETE"])
def delete_todo(req: func.HttpRequest) -> func.HttpResponse:
    todo_id = req.route_params.get("todo_id", "")
    return crud_todos.delete_todo(_resolve_user_id(req), todo_id)


@app.route(route="tools/estimate-hours", methods=["POST"])
def tool_estimate_hours(req: func.HttpRequest) -> func.HttpResponse:
    return estimate_hours.estimate(req, _resolve_user_id(req))


@app.route(route="chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    user_id = _resolve_user_id(req)
    try:
        body = req.get_json()
        message = (body.get("message") or "").strip()
        if not message:
            return func.HttpResponse(
                json.dumps({"error": "message is required"}),
                mimetype="application/json",
                status_code=400,
            )

        conversation_id = (body.get("conversationId") or "").strip() or None
        conversation_doc_id = (body.get("conversationDocId") or "").strip() or None
        result = chat_with_foundry(user_id, message, conversation_id)

        if "error" not in result:
            # Persist messages to Cosmos DB asynchronously (best-effort)
            try:
                saved = crud_conversations.upsert_conversation(
                    user_id=user_id,
                    conversation_id=result["conversationId"],
                    user_message=message,
                    assistant_message=result.get("answer", ""),
                    doc_id=conversation_doc_id,
                )
                result["conversationDocId"] = saved["id"]
            except Exception as save_err:
                logger.warning("Failed to persist conversation: %s", save_err)

            return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json", status_code=200)

        # Keep local UX smooth: when Foundry is not configured, return 200 so frontend can show inline guidance.
        if result.get("status") == "not_configured":
            return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json", status_code=200)

        return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json", status_code=502)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="conversations", methods=["GET"])
def list_conversations(req: func.HttpRequest) -> func.HttpResponse:
    return crud_conversations.list_conversations(_resolve_user_id(req))


@app.route(route="conversations/{doc_id}", methods=["GET"])
def get_conversation(req: func.HttpRequest) -> func.HttpResponse:
    doc_id = req.route_params.get("doc_id", "")
    return crud_conversations.get_conversation(_resolve_user_id(req), doc_id)


@app.route(route="conversations/{doc_id}", methods=["DELETE"])
def delete_conversation(req: func.HttpRequest) -> func.HttpResponse:
    doc_id = req.route_params.get("doc_id", "")
    return crud_conversations.delete_conversation(_resolve_user_id(req), doc_id)


@app.route(route="graph/related", methods=["GET"])
def graph_related(req: func.HttpRequest) -> func.HttpResponse:
    user_id = _resolve_user_id(req)
    todo_id = req.params.get("todoId", "")
    relation = req.params.get("relation", "SIMILAR_TO")
    if not todo_id:
        return func.HttpResponse(
            json.dumps({"error": "todoId is required"}),
            mimetype="application/json",
            status_code=400,
        )

    items = query_related(user_id, todo_id, relation)
    return func.HttpResponse(json.dumps({"items": items}, ensure_ascii=False), mimetype="application/json")
