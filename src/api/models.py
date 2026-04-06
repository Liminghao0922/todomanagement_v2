from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime


class Owner(Base):
    """Owner (user) entity"""
    __tablename__ = "owners"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    todos = relationship("Todo", back_populates="owner", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Owner(id={self.id}, name={self.name}, email={self.email})>"


class Project(Base):
    """Project/Epic entity for task organization"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owners.id"), nullable=False, index=True)
    name = Column(String, nullable=False)  # Project name
    description = Column(Text, nullable=True)  # Project description
    status = Column(String, default="active", index=True)  # 'active', 'completed', 'archived'
    priority = Column(String, default="medium")  # 'low', 'medium', 'high'
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("Owner", back_populates="projects")
    todos = relationship("Todo", back_populates="project_obj", cascade="all, delete-orphan")
    
    # Composite index
    __table_args__ = (
        Index('idx_owner_status', 'owner_id', 'status'),
        Index('idx_owner_created', 'owner_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name}, owner_id={self.owner_id})>"


class Todo(Base):
    """Todo item entity"""
    __tablename__ = "todos"
    
    id = Column(String, primary_key=True, index=True)
    owner_id = Column(String, ForeignKey("owners.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True, index=True)  # Link to Project
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="open", index=True)  # open, completed
    priority = Column(String, default="medium", index=True)  # low, medium, high
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Phase 1: AI-readiness fields
    estimated_hours = Column(Integer, nullable=True)  # Estimated effort
    complexity = Column(String, nullable=True)  # 'simple', 'medium', 'complex'
    category = Column(String, nullable=True, index=True)  # Task category
    
    # Phase 2: Execution tracking fields
    actual_hours = Column(Integer, nullable=True)  # Actual time spent
    dependencies = Column(Text, nullable=True)  # JSON string of dependencies
    required_skills = Column(Text, nullable=True)  # JSON string of required skills
    
    # Completion tracking
    completed_at = Column(DateTime(timezone=True), nullable=True)  # When task was completed
    completed_content = Column(Text, nullable=True)  # Final content/notes on completion
    
    # Relationships
    owner = relationship("Owner", back_populates="todos")
    project_obj = relationship("Project", back_populates="todos")
    
    # Composite index for common queries
    __table_args__ = (
        Index('idx_owner_status_created', 'owner_id', 'status', 'created_at'),
        Index('idx_owner_duedate', 'owner_id', 'due_date'),
        Index('idx_project_status', 'project_id', 'status'),
        Index('idx_owner_category', 'owner_id', 'category'),
    )
    
    def __repr__(self):
        return f"<Todo(id={self.id}, title={self.title}, status={self.status}, owner_id={self.owner_id})>"
