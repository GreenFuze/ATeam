from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Dict, Any

T = TypeVar("T")

@dataclass
class ErrorInfo:
    code: str         # e.g., "redis.unavailable", "ownership.denied"
    message: str
    detail: Optional[Dict[str, Any]] = None

@dataclass
class Result(Generic[T]):
    ok: bool
    value: Optional[T] = None
    error: Optional[ErrorInfo] = None
