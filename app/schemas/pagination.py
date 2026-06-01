"""Pagination schemas."""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination request parameters."""
    offset: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(20, ge=1, le=100, description="Number of records to return")


class PaginationMeta(BaseModel):
    """Pagination metadata in response."""
    offset: int
    limit: int
    total: int
    has_more: bool
    next_offset: int = None


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: list
    pagination: PaginationMeta
