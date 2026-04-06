import os
from datetime import datetime
from typing import Any

import requests


def get_recent_calendar_items(owner_principal: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    tenant_id = os.getenv("GRAPH_TENANT_ID", "").strip()
    client_id = os.getenv("GRAPH_CLIENT_ID", "").strip()
    client_secret = os.getenv("GRAPH_CLIENT_SECRET", "").strip()
    if not tenant_id or not client_id or not client_secret or not owner_principal:
        return []

    token = _get_graph_token(tenant_id, client_id, client_secret)
    if not token:
        return []

    url = f"https://graph.microsoft.com/v1.0/users/{owner_principal}/calendarView"
    params = {
        "startDateTime": start.isoformat(),
        "endDateTime": end.isoformat(),
        "$select": "id,subject,bodyPreview,start,end",
    }
    headers = {
        "Authorization": f"Bearer {token}",
    }

    response = requests.get(url, headers=headers, params=params, timeout=20)
    if response.status_code >= 400:
        return []
    data = response.json()
    return data.get("value", [])


def _get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    response = requests.post(token_url, data=payload, timeout=20)
    if response.status_code >= 400:
        return ""
    return response.json().get("access_token", "")
