from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
import json


class OwnerBase(BaseModel):
    """Base owner schema"""
    name: str
    email: str


class OwnerCreate(OwnerBase):
    """Schema for creating owner"""
    id: Optional[str] = None  # Optional Azure AD account ID from frontend


class OwnerInDB(OwnerBase):
    """Schema for owner in database"""
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectBase(BaseModel):
    """Base project schema"""
    name: str
    description: Optional[str] = None
    status: str = "active"  # 'active', 'completed', 'archived'
    priority: str = "medium"  # 'low', 'medium', 'high'
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectCreate(ProjectBase):
    """Schema for creating project"""
    pass


class ProjectUpdate(BaseModel):
    """Schema for updating project"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ProjectInDB(ProjectBase):
    """Schema for project in database"""
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProjectWithTodos(ProjectInDB):
    """Project with associated todos"""
    todos: List['TodoInDB'] = []


class TodoBase(BaseModel):
    """Base todo schema"""
    title: str
    description: Optional[str] = None
    status: str = "open"
    priority: str = "medium"
    due_date: Optional[datetime] = None
    project_id: Optional[str] = None  # Link to Project
    # Phase 1 fields
    estimated_hours: Optional[int] = None
    complexity: Optional[str] = None  # 'simple', 'medium', 'complex'
    category: Optional[str] = None
    # Phase 2 fields
    actual_hours: Optional[int] = None
    dependencies: Optional[List[str]] = None
    required_skills: Optional[List[str]] = None
    # Completion fields
    completed_at: Optional[datetime] = None
    completed_content: Optional[str] = None


class TodoCreate(TodoBase):
    """Schema for creating todo"""
    
    @field_validator('dependencies', 'required_skills', mode='before')
    @classmethod
    def parse_json_fields(cls, v):
        """Convert JSON strings to lists"""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return v


class TodoUpdate(BaseModel):
    """Schema for updating todo"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    project_id: Optional[str] = None
    # Phase 1 fields
    estimated_hours: Optional[int] = None
    complexity: Optional[str] = None
    category: Optional[str] = None
    # Phase 2 fields
    actual_hours: Optional[int] = None
    dependencies: Optional[List[str]] = None
    required_skills: Optional[List[str]] = None
    # Completion fields
    completed_at: Optional[datetime] = None
    completed_content: Optional[str] = None
    
    @field_validator('dependencies', 'required_skills', mode='before')
    @classmethod
    def parse_json_fields(cls, v):
        """Convert JSON strings to lists"""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return v


class TodoInDB(TodoBase):
    """Schema for todo in database"""
    id: str
    owner_id: str
    project_id: Optional[str] = None
    tags: List[str] = []  # Empty list by default
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @field_validator('dependencies', 'required_skills', mode='before')
    @classmethod
    def parse_json_fields(cls, v):
        """Convert JSON strings to lists"""
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return []
        return v


class TodoListResponse(BaseModel):
    """Response schema for todo list with pagination"""
    items: List[TodoInDB]
    total: int
    offset: int
    pageSize: int
    nextOffset: Optional[int] = None


class ErrorResponse(BaseModel):
    """Error response schema"""
    status: int
    message: str
    error: str


# Rebuild models that have forward references to ensure all types are resolved
ProjectWithTodos.model_rebuild()
TodoListResponse.model_rebuild()
