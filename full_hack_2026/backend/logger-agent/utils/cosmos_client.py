"""Azure Cosmos DB client for persisting agent state and results."""

from __future__ import annotations
from typing import Any

from config.settings import get_settings


def get_cosmos_container():
    """Get a reference to the Cosmos DB container."""
    settings = get_settings()

    if not settings.cosmos_endpoint or not settings.cosmos_key:
        return None

    from azure.cosmos import CosmosClient

    client = CosmosClient(settings.cosmos_endpoint, credential=settings.cosmos_key)
    database = client.get_database_client(settings.cosmos_database)
    container = database.get_container_client(settings.cosmos_container)
    return container


def write_to_cosmos(document: dict[str, Any]) -> str | None:
    """Write a document to Cosmos DB and return the document ID."""
    container = get_cosmos_container()

    if container is None:
        # Cosmos not configured — log locally and return the ID
        print(f"[COSMOS-STUB] Would write document: {document.get('id')}")
        return document.get("id")

    try:
        container.upsert_item(document)
        return document["id"]
    except Exception as e:
        print(f"[COSMOS-ERROR] Failed to write: {e}")
        return document.get("id")
