import os
import json
import time
import urllib.parse
import urllib.request
import logging
from functools import lru_cache

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos import exceptions as cosmos_exceptions
from azure.core.credentials import AccessToken


logger = logging.getLogger(__name__)


class _ImdsManagedIdentityCredential:
    """Lightweight token credential using IMDS to avoid azure.identity runtime issues."""

    def __init__(self, client_id: str | None = None) -> None:
        self._client_id = client_id or ""

    def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        if not scopes:
            raise RuntimeError("At least one scope is required for token acquisition")

        resource = scopes[0]
        if resource.endswith("/.default"):
            resource = resource[: -len("/.default")]

        payload = self._request_token_payload(resource)

        token = payload.get("access_token", "")
        if not token:
            raise RuntimeError("IMDS token response did not include access_token")

        expires_on_raw = payload.get("expires_on")
        try:
            expires_on = int(expires_on_raw)
        except Exception:
            expires_on = int(time.time()) + 300

        return AccessToken(token, expires_on)

    def _request_token_payload(self, resource: str) -> dict:
        identity_endpoint = os.getenv("IDENTITY_ENDPOINT", "")
        identity_header = os.getenv("IDENTITY_HEADER", "")
        if identity_endpoint and identity_header:
            query = {
                "api-version": "2019-08-01",
                "resource": resource,
            }
            if self._client_id:
                query["client_id"] = self._client_id
            url = identity_endpoint + ("&" if "?" in identity_endpoint else "?") + urllib.parse.urlencode(query)
            req = urllib.request.Request(url, headers={"X-IDENTITY-HEADER": identity_header, "Metadata": "true"})
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Failed to acquire managed identity token from IDENTITY_ENDPOINT: {exc}")

        msi_endpoint = os.getenv("MSI_ENDPOINT", "")
        msi_secret = os.getenv("MSI_SECRET", "")
        if msi_endpoint and msi_secret:
            query = {
                "api-version": "2017-09-01",
                "resource": resource,
            }
            if self._client_id:
                query["clientid"] = self._client_id
            url = msi_endpoint + ("&" if "?" in msi_endpoint else "?") + urllib.parse.urlencode(query)
            req = urllib.request.Request(url, headers={"Secret": msi_secret})
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                raise RuntimeError(f"Failed to acquire managed identity token from MSI_ENDPOINT: {exc}")

        query = {
            "api-version": "2018-02-01",
            "resource": resource,
        }
        if self._client_id:
            query["client_id"] = self._client_id
        url = "http://169.254.169.254/metadata/identity/oauth2/token?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, headers={"Metadata": "true"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise RuntimeError(f"Failed to acquire managed identity token from IMDS: {exc}")


def _aad_credential():
    try:
        from azure.identity import DefaultAzureCredential

        return DefaultAzureCredential()
    except Exception as exc:
        logger.warning("DefaultAzureCredential unavailable (%s); falling back to IMDS credential", exc)
        return _ImdsManagedIdentityCredential(client_id=os.getenv("AZURE_CLIENT_ID"))


@lru_cache(maxsize=1)
def _client() -> CosmosClient:
    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    key = os.getenv("COSMOS_KEY")
    auth_mode = os.getenv("COSMOS_AUTH_MODE", "auto").strip().lower()
    if not endpoint:
        raise RuntimeError("COSMOS_ENDPOINT is required")

    if auth_mode == "aad":
        return CosmosClient(endpoint, credential=_aad_credential())

    if auth_mode == "key":
        if not key:
            raise RuntimeError("COSMOS_KEY is required when COSMOS_AUTH_MODE=key")
        return CosmosClient(endpoint, credential=key)

    if key:
        return CosmosClient(endpoint, credential=key)
    return CosmosClient(endpoint, credential=_aad_credential())


@lru_cache(maxsize=1)
def _database_name() -> str:
    return os.getenv("COSMOS_DATABASE_NAME", "todo-db")


def _auto_create_enabled() -> bool:
    # Keep production behavior unchanged unless explicitly enabled.
    env_flag = os.getenv("COSMOS_AUTO_CREATE", "true")
    if env_flag:
        return env_flag.lower() in ("1", "true", "yes", "on")

    # When running the Functions host locally, auto-create missing Cosmos resources
    # even if the endpoint points to a cloud account.
    if not os.getenv("WEBSITE_INSTANCE_ID"):
        return True

    endpoint = os.getenv("COSMOS_ENDPOINT", "").lower()
    return "localhost:8081" in endpoint or "127.0.0.1:8081" in endpoint


@lru_cache(maxsize=1)
def _database_client():
    client = _client()
    db_name = _database_name()
    if _auto_create_enabled():
        try:
            return client.create_database_if_not_exists(id=db_name)
        except cosmos_exceptions.CosmosHttpResponseError as exc:
            # AAD data-plane RBAC cannot create databases; fall back to read if it exists.
            if exc.status_code in (401, 403):
                try:
                    return client.get_database_client(db_name)
                except Exception as e:
                    raise RuntimeError(
                        f"Database '{db_name}' does not exist and AAD credentials lack create permission. "
                        f"Please ensure the database exists or use Primary Key authentication for development. Error: {e}"
                    )
            raise
    return client.get_database_client(db_name)


def _get_container(container_name: str, partition_key_path: str):
    db = _database_client()
    if _auto_create_enabled():
        try:
            return db.create_container_if_not_exists(
                id=container_name,
                partition_key=PartitionKey(path=partition_key_path),
            )
        except cosmos_exceptions.CosmosHttpResponseError as exc:
            if exc.status_code in (401, 403):
                try:
                    return db.get_container_client(container_name)
                except Exception as e:
                    raise RuntimeError(
                        f"Container '{container_name}' does not exist and AAD credentials lack create permission. "
                        f"Please ensure the container exists or use Primary Key authentication for development. Error: {e}"
                    )
            raise
    return db.get_container_client(container_name)


def get_todos_container():
    return _get_container("todos", "/owner_id")


def get_owners_container():
    return _get_container("owners", "/id")


def get_projects_container():
    return _get_container("projects", "/owner_id")


def get_conversations_container():
    return _get_container("conversations", "/owner_id")
