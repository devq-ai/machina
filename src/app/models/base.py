"""
Base Model Module for Machina Registry Service

This module provides the base model class with common fields and functionality
for all database models in the Machina Registry Service. It implements DevQ.ai's
standard ORM patterns with timestamps, soft delete capabilities, and audit trails.

Features:
- Common fields (id, created_at, updated_at) for all models
- Soft delete functionality with deleted_at timestamp
- Audit trail support with created_by and updated_by fields
- JSON serialization methods for API responses
- Validation helpers and common model operations
- Integration with Logfire for model-level observability
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Set, Type, TypeVar, Union

import logfire
from sqlalchemy import Column, Integer, DateTime, String, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import validates

from app.core.database import Base

# Type variable for model inheritance
ModelType = TypeVar("ModelType", bound="BaseModel")


class BaseModel(Base):
    """
    Base model class with common fields and functionality.

    This abstract base class provides common fields and methods that should
    be inherited by all domain models in the Machina Registry Service.

    Attributes:
        id: Primary key using UUID for better distribution
        created_at: Timestamp when the record was created
        updated_at: Timestamp when the record was last updated
        created_by: Optional user ID who created the record
        updated_by: Optional user ID who last updated the record
        deleted_at: Soft delete timestamp (None if not deleted)
        is_active: Boolean flag for active/inactive status
    """

    __abstract__ = True

    # Primary key using UUID for better distribution and security
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique identifier for the record"
    )

    # Timestamp fields for audit trail
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        doc="Timestamp when the record was created"
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
        doc="Timestamp when the record was last updated"
    )

    # Optional audit fields for user tracking
    created_by = Column(
        String(255),
        nullable=True,
        doc="User ID or system identifier who created the record"
    )

    updated_by = Column(
        String(255),
        nullable=True,
        doc="User ID or system identifier who last updated the record"
    )

    # Soft delete support
    deleted_at = Column(
        DateTime,
        nullable=True,
        doc="Timestamp when the record was soft deleted (None if active)"
    )

    # Active status flag
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("TRUE"),
        doc="Boolean flag indicating if the record is active"
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generate table name from class name.

        Converts CamelCase class names to snake_case table names.
        Example: RegistryItem -> registry_items
        """
        import re
        # Convert CamelCase to snake_case and add plural 's'
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', cls.__name__)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
        return f"{name}s" if not name.endswith('s') else name

    def __init__(self, **kwargs):
        """
        Initialize the model with optional field values.

        Args:
            **kwargs: Field values to set on the model
        """
        # Set audit fields if provided
        if 'created_by' in kwargs or 'updated_by' in kwargs:
            self.created_by = kwargs.pop('created_by', None)
            self.updated_by = kwargs.pop('updated_by', None)

        # Call parent constructor
        super().__init__(**kwargs)

        # Log model creation for observability
        logfire.debug(
            f"{self.__class__.__name__} model created",
            model_id=str(self.id) if hasattr(self, 'id') and self.id else "pending",
            model_type=self.__class__.__name__
        )

    def __repr__(self) -> str:
        """
        String representation of the model.

        Returns:
            Human-readable string representation
        """
        return (
            f"<{self.__class__.__name__}("
            f"id={self.id}, "
            f"created_at={self.created_at}, "
            f"is_active={self.is_active}"
            f")>"
        )

    def __str__(self) -> str:
        """
        String representation for display purposes.

        Returns:
            Display-friendly string representation
        """
        return f"{self.__class__.__name__} {self.id}"

    @validates('is_active')
    def validate_is_active(self, key: str, value: Any) -> bool:
        """
        Validate the is_active field.

        Args:
            key: Field name being validated
            value: Value being set

        Returns:
            Validated boolean value
        """
        return bool(value)

    def soft_delete(self, deleted_by: Optional[str] = None) -> None:
        """
        Perform a soft delete on the record.

        Sets deleted_at timestamp and marks as inactive without removing
        the record from the database.

        Args:
            deleted_by: Optional user ID who performed the deletion
        """
        self.deleted_at = datetime.utcnow()
        self.is_active = False
        self.updated_by = deleted_by
        self.updated_at = datetime.utcnow()

        logfire.info(
            f"{self.__class__.__name__} soft deleted",
            model_id=str(self.id),
            deleted_by=deleted_by,
            deleted_at=self.deleted_at.isoformat()
        )

    def restore(self, restored_by: Optional[str] = None) -> None:
        """
        Restore a soft-deleted record.

        Clears the deleted_at timestamp and marks as active.

        Args:
            restored_by: Optional user ID who performed the restoration
        """
        self.deleted_at = None
        self.is_active = True
        self.updated_by = restored_by
        self.updated_at = datetime.utcnow()

        logfire.info(
            f"{self.__class__.__name__} restored",
            model_id=str(self.id),
            restored_by=restored_by
        )

    def update_fields(self, updated_by: Optional[str] = None, **kwargs) -> None:
        """
        Update multiple fields on the model.

        Args:
            updated_by: Optional user ID who performed the update
            **kwargs: Field values to update
        """
        excluded_fields = {'id', 'created_at', 'created_by'}

        for key, value in kwargs.items():
            if key not in excluded_fields and hasattr(self, key):
                setattr(self, key, value)

        self.updated_by = updated_by
        self.updated_at = datetime.utcnow()

        logfire.debug(
            f"{self.__class__.__name__} fields updated",
            model_id=str(self.id),
            updated_fields=list(kwargs.keys()),
            updated_by=updated_by
        )

    def to_dict(self, include_deleted: bool = False, exclude: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        Convert the model to a dictionary for JSON serialization.

        Args:
            include_deleted: Whether to include soft-deleted records
            exclude: Set of field names to exclude from the result

        Returns:
            Dictionary representation of the model
        """
        if not include_deleted and self.deleted_at is not None:
            return {}

        exclude = exclude or set()
        result = {}

        # Get all columns from the model
        mapper = inspect(self.__class__)
        for column in mapper.columns:
            column_name = column.name
            if column_name in exclude:
                continue

            value = getattr(self, column_name)

            # Handle different data types for JSON serialization
            if isinstance(value, datetime):
                result[column_name] = value.isoformat()
            elif isinstance(value, uuid.UUID):
                result[column_name] = str(value)
            else:
                result[column_name] = value

        return result

    def to_json_dict(self, **kwargs) -> Dict[str, Any]:
        """
        Convert to dictionary optimized for JSON API responses.

        Args:
            **kwargs: Additional arguments passed to to_dict()

        Returns:
            JSON-serializable dictionary
        """
        return self.to_dict(**kwargs)

    @property
    def is_deleted(self) -> bool:
        """
        Check if the record is soft deleted.

        Returns:
            True if the record is soft deleted, False otherwise
        """
        return self.deleted_at is not None

    @property
    def age_in_days(self) -> int:
        """
        Calculate the age of the record in days.

        Returns:
            Number of days since the record was created
        """
        if not self.created_at:
            return 0
        return (datetime.utcnow() - self.created_at).days

    @property
    def last_modified_days_ago(self) -> int:
        """
        Calculate days since last modification.

        Returns:
            Number of days since the record was last updated
        """
        if not self.updated_at:
            return 0
        return (datetime.utcnow() - self.updated_at).days

    @classmethod
    def get_table_name(cls) -> str:
        """
        Get the table name for this model.

        Returns:
            Table name as a string
        """
        return cls.__tablename__

    @classmethod
    def get_column_names(cls) -> Set[str]:
        """
        Get all column names for this model.

        Returns:
            Set of column names
        """
        mapper = inspect(cls)
        return {column.name for column in mapper.columns}

    @classmethod
    def create_from_dict(cls: Type[ModelType], data: Dict[str, Any], created_by: Optional[str] = None) -> ModelType:
        """
        Create a new instance from a dictionary.

        Args:
            data: Dictionary containing field values
            created_by: Optional user ID who created the record

        Returns:
            New model instance
        """
        # Filter out None values and invalid fields
        valid_columns = cls.get_column_names()
        filtered_data = {
            key: value for key, value in data.items()
            if key in valid_columns and value is not None
        }

        # Set audit field
        if created_by:
            filtered_data['created_by'] = created_by
            filtered_data['updated_by'] = created_by

        return cls(**filtered_data)

    def validate_model(self) -> Dict[str, Any]:
        """
        Validate the model instance.

        Returns:
            Dictionary containing validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

        # Basic validations
        if not self.id:
            validation_result["errors"].append("ID is required")
            validation_result["is_valid"] = False

        if not self.created_at:
            validation_result["errors"].append("Created timestamp is required")
            validation_result["is_valid"] = False

        if self.deleted_at and self.is_active:
            validation_result["warnings"].append("Record is marked as deleted but still active")

        return validation_result

    def get_changes(self, original_values: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Get changes between current state and original values.

        Args:
            original_values: Dictionary of original field values

        Returns:
            Dictionary mapping field names to old/new value pairs
        """
        changes = {}
        current_values = self.to_dict()

        for field, original_value in original_values.items():
            current_value = current_values.get(field)
            if current_value != original_value:
                changes[field] = {
                    "old": original_value,
                    "new": current_value
                }

        return changes
