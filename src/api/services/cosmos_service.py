import os
from functools import lru_cache

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential


@lru_cache(maxsize=1)
def _client() -> CosmosClient:
    endpoint = os.getenv("COSMOS_ENDPOINT", "")
    key = os.getenv("COSMOS_KEY")
    if not endpoint:
        raise RuntimeError("COSMOS_ENDPOINT is required")

    if key:
        return CosmosClient(endpoint, credential=key)
    return CosmosClient(endpoint, credential=DefaultAzureCredential())


@lru_cache(maxsize=1)
def _database_name() -> str:
    return os.getenv("COSMOS_DATABASE_NAME", "todo-db")


def get_todos_container():
    return _client().get_database_client(_database_name()).get_container_client("todos")


def get_owners_container():
    return _client().get_database_client(_database_name()).get_container_client("owners")


def get_projects_container():
    return _client().get_database_client(_database_name()).get_container_client("projects")
