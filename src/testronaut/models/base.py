"""
Base model classes and utilities for database models.

This module provides the foundation for all database models in the Testronaut application.
It includes base model classes, utility methods, and database configuration.
"""
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import uuid4

from pydantic import field_validator
from sqlmodel import Field, Session, SQLModel, create_engine, select

# Type variable for generic repository
T = TypeVar('T', bound=SQLModel)

class BaseModel(SQLModel):
    """Base model for all database entities with common fields."""
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)

    @field_validator('updated_at', mode='before')
    def set_updated_at(cls, v, info):
        """Set updated_at to current time when model is updated."""
        return datetime.utcnow()

    class Config:
        """Configuration for Pydantic models."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

# Database configuration
DATABASE_URL = "sqlite:///testronaut.db"
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

def create_db_and_tables():
    """Create database and tables if they don't exist."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Get a new database session."""
    with Session(engine) as session:
        yield session

class Repository(Generic[T]):
    """Generic repository class for database operations."""

    def __init__(self, model_class: type[T], session_factory=get_session):
        """
        Initialize the repository.

        Args:
            model_class: The SQLModel class this repository manages
            session_factory: Function that yields database sessions
        """
        self.model_class = model_class
        self.session_factory = session_factory

    def get(self, id: str) -> Optional[T]:
        """
        Get a model instance by ID.

        Args:
            id: The unique identifier

        Returns:
            The model instance or None if not found
        """
        with Session(engine) as session:
            return session.get(self.model_class, id)

    def list(self, skip: int = 0, limit: int = 100, **filters) -> List[T]:
        """
        List model instances with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            **filters: Field-based filters

        Returns:
            List of model instances
        """
        with Session(engine) as session:
            query = select(self.model_class)

            # Apply filters
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    query = query.where(getattr(self.model_class, field) == value)

            return session.exec(query.offset(skip).limit(limit)).all()

    def create(self, model: T) -> T:
        """
        Create a new model instance.

        Args:
            model: The model instance to create

        Returns:
            The created model with ID
        """
        with Session(engine) as session:
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """
        Update a model instance.

        Args:
            id: The unique identifier
            data: Dictionary of fields to update

        Returns:
            The updated model or None if not found
        """
        with Session(engine) as session:
            model = session.get(self.model_class, id)
            if model is None:
                return None

            for field, value in data.items():
                if hasattr(model, field):
                    setattr(model, field, value)

            model.updated_at = datetime.utcnow()
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def delete(self, id: str) -> bool:
        """
        Delete a model instance.

        Args:
            id: The unique identifier

        Returns:
            True if deleted, False if not found
        """
        with Session(engine) as session:
            model = session.get(self.model_class, id)
            if model is None:
                return False

            session.delete(model)
            session.commit()
            return True