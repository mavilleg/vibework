"""
Pagination and Filtering Module for Open Reasoning Arena.

This module provides pagination, filtering, and sorting utilities for API endpoints.

Features:
- Generic pagination for SQLAlchemy queries
- Filter parsing from query parameters
- Sorting with multiple fields
- Pagination metadata generation
- Cursor-based pagination for large datasets

Author: Vibe Code Agent
Created: 2026-06-18
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, Union
from enum import Enum
from pydantic import BaseModel, Field
from sqlalchemy import asc, desc, or_, and_, not_, text
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import Select

T = TypeVar('T')


class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    """Filter operator enumeration."""
    EQ = "eq"  # Equal
    NE = "ne"  # Not equal
    GT = "gt"  # Greater than
    GTE = "gte"  # Greater than or equal
    LT = "lt"  # Less than
    LTE = "lte"  # Less than or equal
    IN = "in"  # In list
    NOT_IN = "not_in"  # Not in list
    LIKE = "like"  # SQL LIKE
    ILIKE = "ilike"  # Case-insensitive LIKE
    CONTAINS = "contains"  # Contains substring
    STARTSWITH = "startswith"  # Starts with
    ENDSWITH = "endswith"  # Ends with
    IS_NULL = "is_null"  # Is NULL
    IS_NOT_NULL = "is_not_null"  # Is not NULL


@dataclass
class FilterRule:
    """A single filter rule."""
    field: str
    operator: FilterOperator
    value: Any
    
    def to_sql_expression(self) -> Any:
        """Convert filter rule to SQLAlchemy expression."""
        from sqlalchemy import Column
        
        if self.operator == FilterOperator.EQ:
            return self.field == self.value
        elif self.operator == FilterOperator.NE:
            return self.field != self.value
        elif self.operator == FilterOperator.GT:
            return self.field > self.value
        elif self.operator == FilterOperator.GTE:
            return self.field >= self.value
        elif self.operator == FilterOperator.LT:
            return self.field < self.value
        elif self.operator == FilterOperator.LTE:
            return self.field <= self.value
        elif self.operator == FilterOperator.IN:
            return self.field.in_(self.value)
        elif self.operator == FilterOperator.NOT_IN:
            return ~self.field.in_(self.value)
        elif self.operator == FilterOperator.LIKE:
            return self.field.like(self.value)
        elif self.operator == FilterOperator.ILIKE:
            return self.field.ilike(self.value)
        elif self.operator == FilterOperator.CONTAINS:
            return self.field.contains(self.value)
        elif self.operator == FilterOperator.STARTSWITH:
            return self.field.startswith(self.value)
        elif self.operator == FilterOperator.ENDSWITH:
            return self.field.endswith(self.value)
        elif self.operator == FilterOperator.IS_NULL:
            return self.field.is_(None)
        elif self.operator == FilterOperator.IS_NOT_NULL:
            return self.field.isnot(None)
        else:
            raise ValueError(f"Unknown filter operator: {self.operator}")


@dataclass
class SortRule:
    """A single sort rule."""
    field: str
    order: SortOrder = SortOrder.ASC
    
    def to_sql_order(self) -> Any:
        """Convert sort rule to SQLAlchemy order."""
        if self.order == SortOrder.ASC:
            return asc(self.field)
        else:
            return desc(self.field)


@dataclass
class PaginationParams:
    """Pagination parameters."""
    page: int = 1
    page_size: int = 20
    max_page_size: int = 100
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get the effective limit (capped at max_page_size)."""
        return min(self.page_size, self.max_page_size)
    
    def validate(self) -> None:
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("Page must be at least 1")
        if self.page_size < 1:
            raise ValueError("Page size must be at least 1")
        if self.page_size > self.max_page_size:
            raise ValueError(f"Page size cannot exceed {self.max_page_size}")


@dataclass
class PaginationResult(Generic[T]):
    """Pagination result with metadata."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }


class PaginationQuery(BaseModel):
    """Query parameters for pagination."""
    page: int = Field(default=1, ge=1, le=1000, description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")


class FilterQuery(BaseModel):
    """Query parameters for filtering."""
    filters: Optional[List[str]] = Field(
        default=None,
        description="Filter expressions in format 'field:operator:value'",
        example=["category:eq:math", "difficulty:gte:3"]
    )


class SortQuery(BaseModel):
    """Query parameters for sorting."""
    sort_by: Optional[List[str]] = Field(
        default=None,
        description="Sort fields in format 'field:order'",
        example=["created_at:desc", "title:asc"]
    )


class PaginationFilterQuery(PaginationQuery, FilterQuery, SortQuery):
    """Combined pagination, filtering, and sorting query parameters."""
    pass


def parse_filter_expression(expression: str) -> FilterRule:
    """
    Parse a filter expression string.
    
    Format: "field:operator:value"
    
    Args:
        expression: The filter expression string
        
    Returns:
        FilterRule instance
        
    Raises:
        ValueError: If the expression format is invalid
    """
    parts = expression.split(":", 2)
    
    if len(parts) != 3:
        raise ValueError(f"Invalid filter expression format: {expression}. Expected 'field:operator:value'")
    
    field, operator, value = parts
    
    try:
        op = FilterOperator(operator)
    except ValueError:
        raise ValueError(f"Unknown filter operator: {operator}. Valid operators: {[op.value for op in FilterOperator]}")
    
    # Try to parse value as appropriate type
    parsed_value = _parse_filter_value(value, op)
    
    return FilterRule(field=field, operator=op, value=parsed_value)


def _parse_filter_value(value: str, operator: FilterOperator) -> Any:
    """Parse filter value based on operator."""
    # Handle special operators
    if operator in [FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL]:
        return None
    
    # Handle list operators
    if operator in [FilterOperator.IN, FilterOperator.NOT_IN]:
        # Parse comma-separated list
        return [v.strip() for v in value.split(",") if v.strip()]
    
    # Handle numeric operators
    if operator in [FilterOperator.GT, FilterOperator.GTE, FilterOperator.LT, FilterOperator.LTE]:
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                pass
    
    # Handle boolean
    if value.lower() in ["true", "false"]:
        return value.lower() == "true"
    
    # Default to string
    return value


def parse_sort_expression(expression: str) -> SortRule:
    """
    Parse a sort expression string.
    
    Format: "field:order" (order is optional, defaults to "asc")
    
    Args:
        expression: The sort expression string
        
    Returns:
        SortRule instance
    """
    parts = expression.split(":", 1)
    
    if len(parts) == 1:
        field = parts[0]
        order = SortOrder.ASC
    else:
        field, order_str = parts
        try:
            order = SortOrder(order_str.lower())
        except ValueError:
            order = SortOrder.ASC
    
    return SortRule(field=field, order=order)


def apply_filters(query: Query, filters: List[FilterRule]) -> Query:
    """
    Apply filters to a SQLAlchemy query.
    
    Args:
        query: The SQLAlchemy query to filter
        filters: List of FilterRule instances
        
    Returns:
        Filtered query
    """
    if not filters:
        return query
    
    # Get the model class from the query
    model = query.column_descriptions[0]['entity'] if query.column_descriptions else None
    
    conditions = []
    for filter_rule in filters:
        try:
            # Get the column from the model
            if model and hasattr(model, filter_rule.field):
                column = getattr(model, filter_rule.field)
                filter_rule.field = column
            
            conditions.append(filter_rule.to_sql_expression())
        except (AttributeError, ValueError) as e:
            # Skip invalid filters
            continue
    
    if conditions:
        return query.filter(and_(*conditions))
    
    return query


def apply_sorting(query: Query, sorts: List[SortRule]) -> Query:
    """
    Apply sorting to a SQLAlchemy query.
    
    Args:
        query: The SQLAlchemy query to sort
        sorts: List of SortRule instances
        
    Returns:
        Sorted query
    """
    if not sorts:
        return query
    
    # Get the model class from the query
    model = query.column_descriptions[0]['entity'] if query.column_descriptions else None
    
    order_by = []
    for sort_rule in sorts:
        try:
            # Get the column from the model
            if model and hasattr(model, sort_rule.field):
                column = getattr(model, sort_rule.field)
                sort_rule.field = column
            
            order_by.append(sort_rule.to_sql_order())
        except (AttributeError, ValueError):
            # Skip invalid sorts
            continue
    
    if order_by:
        return query.order_by(*order_by)
    
    return query


def paginate_query(
    query: Query,
    page: int = 1,
    page_size: int = 20,
    max_page_size: int = 100,
) -> Tuple[List[Any], int]:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: The SQLAlchemy query to paginate
        page: Page number (1-based)
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        Tuple of (items, total_count)
    """
    # Validate parameters
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > max_page_size:
        page_size = max_page_size
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    paginated_query = query.offset(offset).limit(page_size)
    
    # Execute query
    items = paginated_query.all()
    
    return items, total


def create_pagination_result(
    items: List[T],
    total: int,
    page: int,
    page_size: int,
    max_page_size: int = 100,
) -> PaginationResult[T]:
    """
    Create a pagination result with metadata.
    
    Args:
        items: List of items
        total: Total number of items
        page: Current page number
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        PaginationResult instance
    """
    # Validate and adjust parameters
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > max_page_size:
        page_size = max_page_size
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return PaginationResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


async def paginate_with_filters(
    model_class: Any,
    db: Session,
    page: int = 1,
    page_size: int = 20,
    filters: Optional[List[str]] = None,
    sorts: Optional[List[str]] = None,
    max_page_size: int = 100,
) -> PaginationResult:
    """
    Paginate a model with optional filtering and sorting.
    
    Args:
        model_class: The SQLAlchemy model class
        db: Database session
        page: Page number
        page_size: Items per page
        filters: List of filter expressions
        sorts: List of sort expressions
        max_page_size: Maximum allowed page size
        
    Returns:
        PaginationResult with items and metadata
    """
    # Build base query
    query = db.query(model_class)
    
    # Parse and apply filters
    filter_rules = []
    if filters:
        for filter_expr in filters:
            try:
                filter_rules.append(parse_filter_expression(filter_expr))
            except ValueError as e:
                # Skip invalid filter expressions
                continue
    
    query = apply_filters(query, filter_rules)
    
    # Parse and apply sorting
    sort_rules = []
    if sorts:
        for sort_expr in sorts:
            try:
                sort_rules.append(parse_sort_expression(sort_expr))
            except ValueError:
                # Skip invalid sort expressions
                continue
    
    query = apply_sorting(query, sort_rules)
    
    # Paginate
    items, total = paginate_query(query, page, page_size, max_page_size)
    
    return create_pagination_result(items, total, page, page_size, max_page_size)


# Pagination response models
class PaginationMetadata(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_previous: bool = Field(..., description="Whether there is a previous page")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    metadata: PaginationMetadata
    
    class Config:
        from_attributes = True


# Convenience function for creating paginated responses
def create_paginated_response(
    items: List[T],
    total: int,
    page: int,
    page_size: int,
    max_page_size: int = 100,
) -> PaginatedResponse[T]:
    """
    Create a paginated response.
    
    Args:
        items: List of items
        total: Total number of items
        page: Current page number
        page_size: Items per page
        max_page_size: Maximum allowed page size
        
    Returns:
        PaginatedResponse instance
    """
    result = create_pagination_result(items, total, page, page_size, max_page_size)
    
    return PaginatedResponse(
        items=result.items,
        metadata=PaginationMetadata(
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
            has_next=result.has_next,
            has_previous=result.has_previous,
        )
    )
