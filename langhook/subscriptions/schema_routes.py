"""Schema management API routes."""

from typing import Any
import structlog
from fastapi import APIRouter, HTTPException, status

from langhook.subscriptions.schema_registry import schema_registry_service

logger = structlog.get_logger("langhook")

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/")
async def get_event_schema() -> dict[str, Any]:
    """
    Get the event schema registry with all known publishers, resource types, and actions.
    
    Returns:
        Dictionary containing:
        - publishers: List of all known publishers
        - resource_types: Dictionary mapping publishers to their resource types  
        - actions: List of all known actions
    """
    return await schema_registry_service.get_schema_summary()


@router.delete("/publishers/{publisher}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_publisher(publisher: str) -> None:
    """
    Delete all schema entries for a publisher.
    
    Args:
        publisher: Publisher name to delete
        
    Raises:
        HTTPException: 404 if publisher not found, 500 for server errors
    """
    try:
        deleted = await schema_registry_service.delete_publisher(publisher)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Publisher '{publisher}' not found"
            )
            
        logger.info(
            "Publisher deleted via API",
            publisher=publisher
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete publisher",
            publisher=publisher,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete publisher"
        ) from e


@router.delete("/publishers/{publisher}/resource-types/{resource_type}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource_type(publisher: str, resource_type: str) -> None:
    """
    Delete all schema entries for a publisher/resource_type combination.
    
    Args:
        publisher: Publisher name
        resource_type: Resource type to delete
        
    Raises:
        HTTPException: 404 if combination not found, 500 for server errors
    """
    try:
        deleted = await schema_registry_service.delete_resource_type(publisher, resource_type)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resource type '{resource_type}' not found for publisher '{publisher}'"
            )
            
        logger.info(
            "Resource type deleted via API",
            publisher=publisher,
            resource_type=resource_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete resource type",
            publisher=publisher,
            resource_type=resource_type,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resource type"
        ) from e


@router.delete("/publishers/{publisher}/resource-types/{resource_type}/actions/{action}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action(publisher: str, resource_type: str, action: str) -> None:
    """
    Delete a specific schema entry.
    
    Args:
        publisher: Publisher name
        resource_type: Resource type
        action: Action to delete
        
    Raises:
        HTTPException: 404 if entry not found, 500 for server errors
    """
    try:
        deleted = await schema_registry_service.delete_action(publisher, resource_type, action)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Action '{action}' not found for publisher '{publisher}' and resource type '{resource_type}'"
            )
            
        logger.info(
            "Action deleted via API",
            publisher=publisher,
            resource_type=resource_type,
            action=action
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete action",
            publisher=publisher,
            resource_type=resource_type,
            action=action,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete action"
        ) from e