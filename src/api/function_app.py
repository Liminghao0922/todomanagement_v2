import json
import logging
from datetime import datetime, timezone

import azure.functions as func

from functions import crud_todos, extract_action_items
from functions.auto_scan_calendar import auto_scan_calendar_timer
from services.foundry_service import chat_with_foundry
from services.graph_service import query_related

logger = logging.getLogger(__name__)
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


def _resolve_user_id(req: func.HttpRequest) -> str:
    # Use header/userId query fallback to keep compatibility while auth is evolving.
    return req.headers.get("x-user-id") or req.params.get("userId") or "demo-user"


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


@app.route(route="todos/{todo_id}", methods=["PATCH"])
def update_todo(req: func.HttpRequest) -> func.HttpResponse:
    todo_id = req.route_params.get("todo_id", "")
    return crud_todos.update_todo(req, _resolve_user_id(req), todo_id)


@app.route(route="todos/{todo_id}", methods=["DELETE"])
def delete_todo(req: func.HttpRequest) -> func.HttpResponse:
    todo_id = req.route_params.get("todo_id", "")
    return crud_todos.delete_todo(_resolve_user_id(req), todo_id)


@app.route(route="tools/extract-action-items", methods=["POST"])
def tool_extract_action_items(req: func.HttpRequest) -> func.HttpResponse:
    return extract_action_items.extract(req)


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

        result = chat_with_foundry(user_id, message)
        code = 200 if "error" not in result else 502
        return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json", status_code=code)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            mimetype="application/json",
            status_code=500,
        )


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


# Timer trigger for automatic meeting action item extraction.
@app.timer_trigger(schedule="0 0 */6 * * *", arg_name="timer", run_on_startup=False, use_monitor=True)
def calendar_scan_job(timer: func.TimerRequest) -> None:
    auto_scan_calendar_timer(timer)
