"""
Custom JSON encoders for serializing complex objects.
"""

import datetime
import enum
import json
from typing import Any

from pydantic import BaseModel


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively sanitize an object for JSON serialization.

    Args:
        obj: The object to sanitize.

    Returns:
        A JSON-serializable representation of the object.
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, enum.Enum):
        return obj.value
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, BaseModel):
        return sanitize_for_json(obj.model_dump(mode="json"))
    elif hasattr(obj, "__dict__"):
        return sanitize_for_json(obj.__dict__)
    else:
        try:
            return str(obj)
        except Exception:
            return None


class CLIToolJSONEncoder(json.JSONEncoder):
    """
    JSON encoder for CLI tool objects.
    Handles Pydantic models, enums, datetime objects, and sets.
    """

    def default(self, obj: Any) -> Any:
        """
        Default serialization method for objects.

        Args:
            obj: The object to serialize.

        Returns:
            A JSON-serializable representation of the object.
        """
        try:
            if isinstance(obj, BaseModel):
                return sanitize_for_json(obj.model_dump(mode="json"))
            elif isinstance(obj, datetime.datetime):
                return obj.isoformat()
            elif isinstance(obj, enum.Enum):
                return obj.value
            elif isinstance(obj, set):
                return list(obj)
            elif hasattr(obj, "model_dump"):
                return sanitize_for_json(obj.model_dump(mode="json"))
            elif hasattr(obj, "__dict__"):
                return sanitize_for_json(obj.__dict__)
            return super().default(obj)
        except Exception as e:
            # Log the error but don't fail serialization
            from testronaut.utils.logging import get_logger

            logger = get_logger(__name__)
            logger.warning(f"Error serializing object of type {type(obj)}: {e}")
            return str(obj)
