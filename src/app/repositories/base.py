"""
Base Repository Module for Machina Registry Service

This module provides the base repository class implementing the repository pattern
with async SQLAlchemy operations. It offers common CRUD operations, query patterns,
and database interaction methods that can be inherited by domain-specific repositories.

Features:
- Generic repository pattern with type safety
- Async SQLAlchemy operations with proper session management
- Common CRUD operations (Create, Read, Update, Delete)
- Advanced querying with filtering, sorting, and pagination
- Soft delete support with restore capabilities
- Bulk operations for performance optimization
- Error handling with custom exceptions
- Logfire integration for database observability
"""

import uuid
from datetime import datetime
from typing import (
    Any, Dict, List, Optional, Sequence, Type, TypeVar, Union,
    Generic, Callable, Tuple
)

import logfire
from sqlalchemy import and_, or_, desc, asc, func, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select

from app.models.base import BaseModel
from app.core.exceptions import (
    DatabaseError,
    NotFoundError,
    ConflictError,
    ValidationError
)

# Type variable for model inheritance
ModelType = TypeVar("ModelType", bound=BaseModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing common database operations.

    This generic repository implements the repository pattern with async SQLAlchemy
    support, providing a consistent interface for database operations across all
    domain models in the Machina Registry Service.

    Type Parameters:
        ModelType: The SQLAlchemy model class this repository manages
    """

    def __init__(self, model: Type[ModelType]):
        """
        Initialize the repository with a model class.

        Args:
            model: SQLAlchemy model class to manage
        """
        self.model = model
        self.model_name = model.__name__

    async def create(
        self,
        db: AsyncSession,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
        created_by: Optional[str] = None,
        commit: bool = True
    ) -> ModelType:
        """
        Create a new record in the database.

        Args:
            db: Database session
            obj_in: Data for creating the record (dict or Pydantic model)
            created_by: Optional user ID who created the record
            commit: Whether to commit the transaction

        Returns:
            Created model instance

        Raises:
            ConflictError: If record already exists (unique constraint violation)
            ValidationError: If data validation fails
            DatabaseError: If database operation fails
        """
        try:
            with logfire.span(f"Create {self.model_name}"):
                # Convert input to dictionary if needed
                if hasattr(obj_in, "dict"):
                    obj_data = obj_in.dict(exclude_unset=True)
                elif hasattr(obj_in, "model_dump"):
                    obj_data = obj_in.model_dump(exclude_unset=True)
                else:
                    obj_data = dict(obj_in) if not isinstance(obj_in, dict) else obj_in.copy()

                # Add audit fields
                if created_by:
                    obj_data["created_by"] = created_by
                    obj_data["updated_by"] = created_by

                # Create model instance
                db_obj = self.model(**obj_data)
                db.add(db_obj)

                if commit:
                    await db.commit()
                    await db.refresh(db_obj)

                logfire.info(
                    f"{self.model_name} created",
                    model_id=str(db_obj.id),
                    created_by=created_by
                )

                return db_obj

        except IntegrityError as e:
            await db.rollback()
            logfire.error(f"Integrity error creating {self.model_name}", error=str(e))
            raise ConflictError(
                resource_type=self.model_name,
                identifier="unknown",
                message=f"Record already exists or violates constraints: {str(e)}",
                cause=e
            )
        except Exception as e:
            await db.rollback()
            logfire.error(f"Error creating {self.model_name}", error=str(e))
            raise DatabaseError(
                operation="create",
                message=f"Failed to create {self.model_name}: {str(e)}",
                cause=e
            )

    async def get(
        self,
        db: AsyncSession,
        id: Union[uuid.UUID, str],
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            db: Database session
            id: Record ID (UUID or string)
            include_deleted: Whether to include soft-deleted records

        Returns:
            Model instance or None if not found
        """
        try:
            with logfire.span(f"Get {self.model_name}"):
                # Convert string to UUID if needed
                if isinstance(id, str):
                    id = uuid.UUID(id)

                query = select(self.model).where(self.model.id == id)

                # Filter out soft-deleted records unless requested
                if not include_deleted:
                    query = query.where(self.model.deleted_at.is_(None))

                result = await db.execute(query)
                obj = result.scalar_one_or_none()

                if obj:
                    logfire.debug(f"{self.model_name} found", model_id=str(id))
                else:
                    logfire.debug(f"{self.model_name} not found", model_id=str(id))

                return obj

        except Exception as e:
            logfire.error(f"Error getting {self.model_name}", model_id=str(id), error=str(e))
            raise DatabaseError(
                operation="get",
                message=f"Failed to get {self.model_name}: {str(e)}",
                cause=e
            )

    async def get_by_field(
        self,
        db: AsyncSession,
        field_name: str,
        value: Any,
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        Get a record by a specific field value.

        Args:
            db: Database session
            field_name: Name of the field to search by
            value: Value to search for
            include_deleted: Whether to include soft-deleted records

        Returns:
            Model instance or None if not found
        """
        try:
            with logfire.span(f"Get {self.model_name} by {field_name}"):
                if not hasattr(self.model, field_name):
                    raise ValidationError(
                        f"Field '{field_name}' does not exist on {self.model_name}",
                        field=field_name,
                        value=value
                    )

                field = getattr(self.model, field_name)
                query = select(self.model).where(field == value)

                if not include_deleted:
                    query = query.where(self.model.deleted_at.is_(None))

                result = await db.execute(query)
                return result.scalar_one_or_none()

        except Exception as e:
            logfire.error(
                f"Error getting {self.model_name} by {field_name}",
                field_name=field_name,
                value=str(value),
                error=str(e)
            )
            raise DatabaseError(
                operation="get_by_field",
                message=f"Failed to get {self.model_name} by {field_name}: {str(e)}",
                cause=e
            )

    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        order_by: Optional[str] = None,
        order_desc: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ModelType]:
        """
        Get multiple records with filtering, sorting, and pagination.

        Args:
            db: Database session
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted records
            order_by: Field name to order by
            order_desc: Whether to order in descending order
            filters: Dictionary of field filters

        Returns:
            List of model instances
        """
        try:
            with logfire.span(f"Get multiple {self.model_name}"):
                query = select(self.model)

                # Apply soft delete filter
                if not include_deleted:
                    query = query.where(self.model.deleted_at.is_(None))

                # Apply filters
                if filters:
                    for field_name, value in filters.items():
                        if hasattr(self.model, field_name):
                            field = getattr(self.model, field_name)
                            if isinstance(value, list):
                                query = query.where(field.in_(value))
                            else:
                                query = query.where(field == value)

                # Apply ordering
                if order_by and hasattr(self.model, order_by):
                    order_field = getattr(self.model, order_by)
                    if order_desc:
                        query = query.order_by(desc(order_field))
                    else:
                        query = query.order_by(asc(order_field))
                else:
                    # Default ordering by created_at desc
                    query = query.order_by(desc(self.model.created_at))

                # Apply pagination
                query = query.offset(skip).limit(limit)

                result = await db.execute(query)
                objects = result.scalars().all()

                logfire.debug(
                    f"Retrieved {len(objects)} {self.model_name} records",
                    count=len(objects),
                    skip=skip,
                    limit=limit
                )

                return list(objects)

        except Exception as e:
            logfire.error(f"Error getting multiple {self.model_name}", error=str(e))
            raise DatabaseError(
                operation="get_multi",
                message=f"Failed to get multiple {self.model_name}: {str(e)}",
                cause=e
            )

    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
        updated_by: Optional[str] = None,
        commit: bool = True
    ) -> ModelType:
        """
        Update an existing record.

        Args:
            db: Database session
            db_obj: Existing model instance to update
            obj_in: Update data (dict or Pydantic model)
            updated_by: Optional user ID who updated the record
            commit: Whether to commit the transaction

        Returns:
            Updated model instance

        Raises:
            ValidationError: If update data is invalid
            DatabaseError: If database operation fails
        """
        try:
            with logfire.span(f"Update {self.model_name}"):
                # Convert input to dictionary if needed
                if hasattr(obj_in, "dict"):
                    obj_data = obj_in.dict(exclude_unset=True)
                elif hasattr(obj_in, "model_dump"):
                    obj_data = obj_in.model_dump(exclude_unset=True)
                else:
                    obj_data = dict(obj_in) if not isinstance(obj_in, dict) else obj_in.copy()

                # Remove fields that shouldn't be updated
                protected_fields = {"id", "created_at", "created_by"}
                for field in protected_fields:
                    obj_data.pop(field, None)

                # Add audit fields
                if updated_by:
                    obj_data["updated_by"] = updated_by

                # Update the object using the model's update_fields method
                db_obj.update_fields(updated_by=updated_by, **obj_data)

                if commit:
                    await db.commit()
                    await db.refresh(db_obj)

                logfire.info(
                    f"{self.model_name} updated",
                    model_id=str(db_obj.id),
                    updated_by=updated_by,
                    updated_fields=list(obj_data.keys())
                )

                return db_obj

        except Exception as e:
            await db.rollback()
            logfire.error(f"Error updating {self.model_name}", model_id=str(db_obj.id), error=str(e))
            raise DatabaseError(
                operation="update",
                message=f"Failed to update {self.model_name}: {str(e)}",
                cause=e
            )

    async def delete(
        self,
        db: AsyncSession,
        id: Union[uuid.UUID, str],
        soft_delete: bool = True,
        deleted_by: Optional[str] = None,
        commit: bool = True
    ) -> bool:
        """
        Delete a record (soft delete by default).

        Args:
            db: Database session
            id: Record ID to delete
            soft_delete: Whether to perform soft delete (default) or hard delete
            deleted_by: Optional user ID who deleted the record
            commit: Whether to commit the transaction

        Returns:
            True if record was deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with logfire.span(f"Delete {self.model_name}"):
                # Get the object first
                obj = await self.get(db, id, include_deleted=False)
                if not obj:
                    return False

                if soft_delete:
                    # Perform soft delete
                    obj.soft_delete(deleted_by=deleted_by)
                else:
                    # Perform hard delete
                    await db.delete(obj)

                if commit:
                    await db.commit()

                delete_type = "soft" if soft_delete else "hard"
                logfire.info(
                    f"{self.model_name} {delete_type} deleted",
                    model_id=str(id),
                    deleted_by=deleted_by
                )

                return True

        except Exception as e:
            await db.rollback()
            logfire.error(f"Error deleting {self.model_name}", model_id=str(id), error=str(e))
            raise DatabaseError(
                operation="delete",
                message=f"Failed to delete {self.model_name}: {str(e)}",
                cause=e
            )

    async def restore(
        self,
        db: AsyncSession,
        id: Union[uuid.UUID, str],
        restored_by: Optional[str] = None,
        commit: bool = True
    ) -> bool:
        """
        Restore a soft-deleted record.

        Args:
            db: Database session
            id: Record ID to restore
            restored_by: Optional user ID who restored the record
            commit: Whether to commit the transaction

        Returns:
            True if record was restored, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with logfire.span(f"Restore {self.model_name}"):
                # Get the soft-deleted object
                obj = await self.get(db, id, include_deleted=True)
                if not obj or not obj.is_deleted:
                    return False

                # Restore the object
                obj.restore(restored_by=restored_by)

                if commit:
                    await db.commit()

                logfire.info(
                    f"{self.model_name} restored",
                    model_id=str(id),
                    restored_by=restored_by
                )

                return True

        except Exception as e:
            await db.rollback()
            logfire.error(f"Error restoring {self.model_name}", model_id=str(id), error=str(e))
            raise DatabaseError(
                operation="restore",
                message=f"Failed to restore {self.model_name}: {str(e)}",
                cause=e
            )

    async def count(
        self,
        db: AsyncSession,
        include_deleted: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records with optional filtering.

        Args:
            db: Database session
            include_deleted: Whether to include soft-deleted records
            filters: Dictionary of field filters

        Returns:
            Number of matching records

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            with logfire.span(f"Count {self.model_name}"):
                query = select(func.count(self.model.id))

                # Apply soft delete filter
                if not include_deleted:
                    query = query.where(self.model.deleted_at.is_(None))

                # Apply filters
                if filters:
                    for field_name, value in filters.items():
                        if hasattr(self.model, field_name):
                            field = getattr(self.model, field_name)
                            if isinstance(value, list):
                                query = query.where(field.in_(value))
                            else:
                                query = query.where(field == value)

                result = await db.execute(query)
                count = result.scalar() or 0

                logfire.debug(f"Counted {count} {self.model_name} records")
                return count

        except Exception as e:
            logfire.error(f"Error counting {self.model_name}", error=str(e))
            raise DatabaseError(
                operation="count",
                message=f"Failed to count {self.model_name}: {str(e)}",
                cause=e
            )

    async def exists(
        self,
        db: AsyncSession,
        id: Union[uuid.UUID, str],
        include_deleted: bool = False
    ) -> bool:
        """
        Check if a record exists.

        Args:
            db: Database session
            id: Record ID to check
            include_deleted: Whether to include soft-deleted records

        Returns:
            True if record exists, False otherwise
        """
        obj = await self.get(db, id, include_deleted=include_deleted)
        return obj is not None

    async def bulk_create(
        self,
        db: AsyncSession,
        objs_in: List[Union[CreateSchemaType, Dict[str, Any]]],
        created_by: Optional[str] = None,
        commit: bool = True
    ) -> List[ModelType]:
        """
        Create multiple records in bulk.

        Args:
            db: Database session
            objs_in: List of data for creating records
            created_by: Optional user ID who created the records
            commit: Whether to commit the transaction

        Returns:
            List of created model instances

        Raises:
            DatabaseError: If bulk operation fails
        """
        try:
            with logfire.span(f"Bulk create {self.model_name}"):
                db_objs = []

                for obj_in in objs_in:
                    # Convert input to dictionary if needed
                    if hasattr(obj_in, "dict"):
                        obj_data = obj_in.dict(exclude_unset=True)
                    elif hasattr(obj_in, "model_dump"):
                        obj_data = obj_in.model_dump(exclude_unset=True)
                    else:
                        obj_data = dict(obj_in) if not isinstance(obj_in, dict) else obj_in.copy()

                    # Add audit fields
                    if created_by:
                        obj_data["created_by"] = created_by
                        obj_data["updated_by"] = created_by

                    db_obj = self.model(**obj_data)
                    db_objs.append(db_obj)

                db.add_all(db_objs)

                if commit:
                    await db.commit()
                    for db_obj in db_objs:
                        await db.refresh(db_obj)

                logfire.info(
                    f"Bulk created {len(db_objs)} {self.model_name} records",
                    count=len(db_objs),
                    created_by=created_by
                )

                return db_objs

        except Exception as e:
            await db.rollback()
            logfire.error(f"Error bulk creating {self.model_name}", error=str(e))
            raise DatabaseError(
                operation="bulk_create",
                message=f"Failed to bulk create {self.model_name}: {str(e)}",
                cause=e
            )

    async def search(
        self,
        db: AsyncSession,
        search_term: str,
        search_fields: List[str],
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """
        Search records across multiple fields.

        Args:
            db: Database session
            search_term: Term to search for
            search_fields: List of field names to search in
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of matching model instances
        """
        try:
            with logfire.span(f"Search {self.model_name}"):
                query = select(self.model)

                # Apply soft delete filter
                if not include_deleted:
                    query = query.where(self.model.deleted_at.is_(None))

                # Build search conditions
                search_conditions = []
                for field_name in search_fields:
                    if hasattr(self.model, field_name):
                        field = getattr(self.model, field_name)
                        # Use ILIKE for case-insensitive search
                        search_conditions.append(field.ilike(f"%{search_term}%"))

                if search_conditions:
                    query = query.where(or_(*search_conditions))

                # Apply pagination
                query = query.offset(skip).limit(limit)
                query = query.order_by(desc(self.model.created_at))

                result = await db.execute(query)
                objects = result.scalars().all()

                logfire.debug(
                    f"Search found {len(objects)} {self.model_name} records",
                    search_term=search_term,
                    search_fields=search_fields,
                    count=len(objects)
                )

                return list(objects)

        except Exception as e:
            logfire.error(f"Error searching {self.model_name}", error=str(e))
            raise DatabaseError(
                operation="search",
                message=f"Failed to search {self.model_name}: {str(e)}",
                cause=e
            )
