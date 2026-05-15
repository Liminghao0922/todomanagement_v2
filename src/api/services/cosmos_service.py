import os
from functools import lru_cache

from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos import exceptions as cosmos_exceptions
from azure.identity import DefaultAzureCredential


@lru_cache(maxsize=1)
def _client() -> CosmosClient:
    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    key = os.getenv("COSMOS_KEY")
    auth_mode = os.getenv("COSMOS_AUTH_MODE", "auto").strip().lower()
    if not endpoint:
        raise RuntimeError("COSMOS_ENDPOINT is required")

    if auth_mode == "aad":
        return CosmosClient(endpoint, credential=DefaultAzureCredential())

    if auth_mode == "key":
        if not key:
            raise RuntimeError("COSMOS_KEY is required when COSMOS_AUTH_MODE=key")
        return CosmosClient(endpoint, credential=key)

    if key:
        return CosmosClient(endpoint, credential=key)
    return CosmosClient(endpoint, credential=DefaultAzureCredential())


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
