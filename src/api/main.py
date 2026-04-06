import uuid
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from config import settings
from database import get_db, init_db
from models import Owner, Todo, Project
from schemas import (
    TodoCreate, TodoUpdate, TodoInDB, TodoListResponse,
    OwnerCreate, OwnerInDB,
    ProjectCreate, ProjectUpdate, ProjectInDB, ProjectWithTodos
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Todo Management API"
)

# Initialize database (after models are imported)
try:
    init_db()
except Exception as e:
    logger.warning(f"Database initialization warning (may be normal in testing): {e}")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Container Apps"""
    return {
        "status": "healthy",
        "service": "Todo Management API",
        "version": settings.api_version
    }


# ============ OWNER ENDPOINTS ============

@app.post("/api/owners", response_model=OwnerInDB)
async def create_owner(owner: OwnerCreate, db: Session = Depends(get_db)):
    """Create a new owner (user)"""
    try:
        # Check if email already exists
        existing = db.query(Owner).filter(Owner.email == owner.email).first()
        if existing:
            logger.info(f"✓ Owner already exists: {existing.id}")
            return existing  # 直接返回已存在的owner
        
        # Create new owner using provided ID or generate new one
        owner_id = owner.id or str(uuid.uuid4())
        new_owner = Owner(
            id=owner_id,
            name=owner.name,
            email=owner.email
        )
        db.add(new_owner)
        db.commit()
        db.refresh(new_owner)
        
        logger.info(f"✓ Created owner: {new_owner.id}")
        return new_owner
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating owner: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/owners/{owner_id}", response_model=OwnerInDB)
async def get_owner(owner_id: str, db: Session = Depends(get_db)):
    """Get owner by ID"""
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return owner


# ============ PROJECT ENDPOINTS ============

@app.post("/api/projects", response_model=ProjectInDB)
async def create_project(
    project: ProjectCreate,
    userId: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create a new project for a user"""
    try:
        # Verify owner exists
        owner = db.query(Owner).filter(Owner.id == userId).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        
        # Create new project
        new_project = Project(
            id=str(uuid.uuid4()),
            owner_id=userId,
            name=project.name,
            description=project.description,
            status=project.status,
            priority=project.priority,
            start_date=project.start_date,
            end_date=project.end_date
        )
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        logger.info(f"✓ Created project: {new_project.id} for owner {userId}")
        return new_project
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects", response_model=list[ProjectInDB])
async def list_projects(
    userId: str = Query(...),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """List projects for a user"""
    try:
        query = db.query(Project).filter(Project.owner_id == userId)
        
        if status:
            query = query.filter(Project.status == status)
        
        projects = query.order_by(desc(Project.created_at)).all()
        return projects
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}", response_model=ProjectWithTodos)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a specific project with its todos"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.patch("/api/projects/{project_id}", response_model=ProjectInDB)
async def update_project(
    project_id: str,
    update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update a project"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Update fields
        if update.name is not None:
            project.name = update.name
        if update.description is not None:
            project.description = update.description
        if update.status is not None:
            project.status = update.status
        if update.priority is not None:
            project.priority = update.priority
        if update.start_date is not None:
            project.start_date = update.start_date
        if update.end_date is not None:
            project.end_date = update.end_date
        
        project.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        
        logger.info(f"✓ Updated project: {project_id}")
        return project
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project"""
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        db.delete(project)
        db.commit()
        
        logger.info(f"✓ Deleted project: {project_id}")
        return {"status": "deleted", "id": project_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ PROJECT ALIAS ROUTES (without /api prefix) ============

@app.post("/projects", response_model=ProjectInDB)
async def create_project_alias(
    project: ProjectCreate,
    userId: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create a new project (alias for /api/projects)"""
    return await create_project(project, userId, db)


@app.get("/projects", response_model=list[ProjectInDB])
async def list_projects_alias(
    userId: str = Query(...),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """List projects for a user (alias for /api/projects)"""
    return await list_projects(userId, status, db)


@app.get("/projects/{project_id}", response_model=ProjectWithTodos)
async def get_project_alias(project_id: str, db: Session = Depends(get_db)):
    """Get a specific project (alias for /api/projects/{project_id})"""
    return await get_project(project_id, db)


@app.patch("/projects/{project_id}", response_model=ProjectInDB)
async def update_project_alias(
    project_id: str,
    update: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """Update a project (alias for /api/projects/{project_id})"""
    return await update_project(project_id, update, db)


@app.delete("/projects/{project_id}")
async def delete_project_alias(project_id: str, db: Session = Depends(get_db)):
    """Delete a project (alias for /api/projects/{project_id})"""
    return await delete_project(project_id, db)


# ============ TODO ENDPOINTS ============

class TodoCreateRequest(BaseModel):
    """Request model for creating a todo - includes userId"""
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    dueDate: Optional[datetime] = None
    tags: list = []
    userId: str  # Required in request body
    # Phase 1: AI-readiness fields
    estimatedHours: Optional[int] = None
    complexity: Optional[str] = None  # 'simple', 'medium', 'complex'
    projectId: Optional[str] = None  # Link to Project entity
    category: Optional[str] = None
    # Phase 2: Execution tracking fields
    actualHours: Optional[int] = None
    dependencies: Optional[list] = None
    requiredSkills: Optional[list] = None
    # Completion tracking
    completedAt: Optional[datetime] = None
    completedContent: Optional[str] = None


@app.post("/api/todos", response_model=TodoInDB)
async def create_todo(
    request: TodoCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new todo"""
    try:
        # Verify owner exists
        owner = db.query(Owner).filter(Owner.id == request.userId).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        
        # Create new todo
        import json
        new_todo = Todo(
            id=str(uuid.uuid4()),
            owner_id=request.userId,
            title=request.title,
            description=request.description,
            status=request.status,
            priority=request.priority,
            due_date=request.dueDate,
            # Phase 1 fields
            estimated_hours=request.estimatedHours,
            complexity=request.complexity,
            project_id=request.projectId,  # Link to Project entity
            category=request.category,
            # Phase 2 fields
            actual_hours=request.actualHours,
            dependencies=json.dumps(request.dependencies) if request.dependencies else None,
            required_skills=json.dumps(request.requiredSkills) if request.requiredSkills else None,
            # Completion fields
            completed_at=request.completedAt,
            completed_content=request.completedContent
        )
        db.add(new_todo)
        db.commit()
        db.refresh(new_todo)
        
        logger.info(f"✓ Created todo: {new_todo.id} for owner {request.userId}")
        return new_todo
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating todo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/todos", response_model=TodoListResponse)
async def list_todos(
    userId: str = Query(...),
    offset: int = Query(0, ge=0),
    pageSize: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    dueDateStart: str = Query(None),
    dueDateEnd: str = Query(None),
    projectId: str = Query(None),
    category: str = Query(None),
    complexity: str = Query(None),
    db: Session = Depends(get_db)
):
    """List todos for an owner with filtering and pagination"""
    try:
        # Base query
        query = db.query(Todo).filter(Todo.owner_id == userId)
        
        # Apply filters
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Todo.title.ilike(search_term),
                    Todo.description.ilike(search_term)
                )
            )
        if status:
            query = query.filter(Todo.status == status)
        if priority:
            query = query.filter(Todo.priority == priority)
        if projectId:
            query = query.filter(Todo.project_id == projectId)
        if category:
            query = query.filter(Todo.category == category)
        if complexity:
            query = query.filter(Todo.complexity == complexity)
        
        # Apply date range filters
        if dueDateStart:
            try:
                # Handle both date-only (YYYY-MM-DD) and datetime formats
                if 'T' in dueDateStart:
                    start_date = datetime.fromisoformat(dueDateStart.replace('Z', '+00:00'))
                else:
                    start_date = datetime.fromisoformat(dueDateStart + 'T00:00:00')
                query = query.filter(Todo.due_date >= start_date)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid dueDateStart format: {dueDateStart}, error: {e}")
        
        if dueDateEnd:
            try:
                # Handle both date-only (YYYY-MM-DD) and datetime formats
                if 'T' in dueDateEnd:
                    end_date = datetime.fromisoformat(dueDateEnd.replace('Z', '+00:00'))
                else:
                    end_date = datetime.fromisoformat(dueDateEnd + 'T23:59:59')
                query = query.filter(Todo.due_date <= end_date)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid dueDateEnd format: {dueDateEnd}, error: {e}")
        
        # Get total count
        total = query.count()
        
        # Apply pagination (offset/limit)
        todos = query.order_by(desc(Todo.created_at)).offset(offset).limit(pageSize).all()
        
        # Calculate next offset
        next_offset = offset + pageSize if offset + pageSize < total else None
        
        return TodoListResponse(
            items=todos,
            total=total,
            offset=offset,
            pageSize=pageSize,
            nextOffset=next_offset
        )
    except Exception as e:
        logger.error(f"Error listing todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ ALIAS ROUTES (without /api prefix) ============

@app.post("/todos", response_model=TodoInDB)
async def create_todo_alias(
    request: TodoCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new todo (alias for /api/todos)"""
    return await create_todo(request, db)


@app.get("/todos", response_model=TodoListResponse)
async def list_todos_alias(
    userId: str = Query(...),
    offset: int = Query(0, ge=0),
    pageSize: int = Query(10, ge=1, le=100),
    search: str = Query(None),
    status: str = Query(None),
    priority: str = Query(None),
    dueDateStart: str = Query(None),
    dueDateEnd: str = Query(None),
    projectId: str = Query(None),
    category: str = Query(None),
    complexity: str = Query(None),
    db: Session = Depends(get_db)
):
    """List todos for an owner (alias for /api/todos)"""
    return await list_todos(userId, offset, pageSize, search, status, priority, dueDateStart, dueDateEnd, projectId, category, complexity, db)


@app.get("/api/todos/{todo_id}", response_model=TodoInDB)
async def get_todo(todo_id: str, db: Session = Depends(get_db)):
    """Get a specific todo"""
    todo = db.query(Todo).filter(Todo.id == todo_id).first()
    if not todo:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todo


@app.patch("/api/todos/{todo_id}", response_model=TodoInDB)
async def update_todo(
    todo_id: str,
    update: TodoUpdate,
    db: Session = Depends(get_db)
):
    """Update a todo"""
    try:
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        # Update fields
        import json
        if update.title is not None:
            todo.title = update.title
        if update.description is not None:
            todo.description = update.description
        if update.status is not None:
            todo.status = update.status
        if update.priority is not None:
            todo.priority = update.priority
        if update.due_date is not None:
            todo.due_date = update.due_date
        # Phase 1 fields
        if update.estimated_hours is not None:
            todo.estimated_hours = update.estimated_hours
        if update.complexity is not None:
            todo.complexity = update.complexity
        if update.project_id is not None:
            todo.project_id = update.project_id
        if update.category is not None:
            todo.category = update.category
        # Phase 2 fields
        if update.actual_hours is not None:
            todo.actual_hours = update.actual_hours
        if update.dependencies is not None:
            todo.dependencies = json.dumps(update.dependencies) if update.dependencies else None
        if update.required_skills is not None:
            todo.required_skills = json.dumps(update.required_skills) if update.required_skills else None
        # Completion fields
        if update.completed_at is not None:
            todo.completed_at = update.completed_at
        if update.completed_content is not None:
            todo.completed_content = update.completed_content
        
        todo.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(todo)
        
        logger.info(f"✓ Updated todo: {todo_id}")
        return todo
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating todo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/todos/{todo_id}")
async def delete_todo(todo_id: str, db: Session = Depends(get_db)):
    """Delete a todo"""
    try:
        todo = db.query(Todo).filter(Todo.id == todo_id).first()
        if not todo:
            raise HTTPException(status_code=404, detail="Todo not found")
        
        db.delete(todo)
        db.commit()
        
        logger.info(f"✓ Deleted todo: {todo_id}")
        return {"status": "deleted", "id": todo_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting todo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ MORE ALIAS ROUTES ============

@app.get("/todos/{todo_id}", response_model=TodoInDB)
async def get_todo_alias(todo_id: str, db: Session = Depends(get_db)):
    """Get a specific todo (alias for /api/todos/{todo_id})"""
    return await get_todo(todo_id, db)


@app.patch("/todos/{todo_id}", response_model=TodoInDB)
async def update_todo_alias(
    todo_id: str,
    update: TodoUpdate,
    db: Session = Depends(get_db)
):
    """Update a todo (alias for /api/todos/{todo_id})"""
    return await update_todo(todo_id, update, db)


@app.delete("/todos/{todo_id}")
async def delete_todo_alias(todo_id: str, db: Session = Depends(get_db)):
    """Delete a todo (alias for /api/todos/{todo_id})"""
    return await delete_todo(todo_id, db)


# ============ TEST DATA GENERATION ============

@app.post("/api/generate-todos")
async def generate_test_todos(
    userId: str = Query(...),
    count: int = Query(10, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """Generate test todos for a user with all new fields"""
    import time
    import random
    import json
    from datetime import timedelta
    from string import ascii_letters, digits
    
    start_time = time.time()
    
    try:
        # Verify user exists
        owner = db.query(Owner).filter(Owner.id == userId).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
        
        # Get user's projects for random assignment
        projects = db.query(Project).filter(Project.owner_id == userId).all()
        project_ids = [p.id for p in projects] if projects else []
        
        # Sample data for generating todos
        titles = [
            "Complete project documentation",
            "Review pull requests",
            "Update dependencies",
            "Fix bug in authentication",
            "Write unit tests",
            "Optimize database queries",
            "Update README",
            "Schedule team meeting",
            "Prepare presentation",
            "Code review",
            "Refactor legacy code",
            "Setup CI/CD pipeline",
            "Deploy to production",
            "Monitor system performance",
            "Update API documentation",
        ]
        
        descriptions = [
            "High priority task",
            "Need to complete ASAP",
            "Follow up with team",
            "Review and approve",
            "Testing required",
            "Documentation needed",
            "Performance improvement",
            "Bug fix and testing",
            "Implement new feature",
            "Code cleanup",
        ]
        
        statuses = ["pending", "in-progress", "completed"]
        priorities = ["low", "medium", "high"]
        complexities = ["simple", "medium", "complex"]
        categories = ["feature", "bug", "refactor", "documentation", "optimization", "testing"]
        
        # Sample skills for dependencies
        skills = ["Python", "JavaScript", "SQL", "Testing", "Documentation", "DevOps", "Code Review"]
        
        # Generate todos
        created_count = 0
        for i in range(count):
            try:
                # Generate random due date: between -30 and +90 days from today
                days_offset = random.randint(-30, 90)
                due_date = datetime.utcnow() + timedelta(days=days_offset)
                
                # Randomly select status
                status = random.choice(statuses)
                
                # Generate completion timestamp if completed
                completed_at = None
                completed_content = None
                if status == "completed":
                    # Complete somewhere between due_date and today
                    days_before = random.randint(0, 30)
                    completed_at = datetime.utcnow() - timedelta(days=days_before)
                    completed_content = f"Completed and tested. All requirements met."
                
                # Generate estimated hours (5-40 hours)
                estimated_hours = random.randint(5, 40)
                
                # Generate actual hours if completed
                actual_hours = None
                if status == "completed":
                    # Actual hours usually close to estimated
                    variance = random.randint(-10, 20)
                    actual_hours = max(1, estimated_hours + variance // 2)
                
                # Generate random dependencies (as JSON string)
                dependencies = None
                if random.random() > 0.6:  # 40% chance of having dependencies
                    deps = [titles[random.randint(0, len(titles)-1)] for _ in range(random.randint(1, 3))]
                    dependencies = json.dumps(deps)
                
                # Generate required skills (as JSON string)
                required_skills = None
                if random.random() > 0.5:  # 50% chance of having required skills
                    reqs = random.sample(skills, k=random.randint(1, 3))
                    required_skills = json.dumps(reqs)
                
                new_todo = Todo(
                    id=str(uuid.uuid4()),
                    owner_id=userId,
                    project_id=random.choice(project_ids) if project_ids else None,
                    title=f"{random.choice(titles)} #{i+1}",
                    description=random.choice(descriptions) if random.random() > 0.3 else None,
                    status=status,
                    priority=random.choice(priorities),
                    due_date=due_date,
                    # Phase 1 fields
                    estimated_hours=estimated_hours,
                    complexity=random.choice(complexities),
                    category=random.choice(categories),
                    # Phase 2 fields
                    actual_hours=actual_hours,
                    dependencies=dependencies,
                    required_skills=required_skills,
                    # Completion tracking
                    completed_at=completed_at,
                    completed_content=completed_content,
                )
                db.add(new_todo)
                created_count += 1
            except Exception as e:
                logger.warning(f"Failed to create todo {i+1}: {e}")
                continue
        
        db.commit()
        
        elapsed_time = time.time() - start_time
        
        return {
            "success": True,
            "createdCount": created_count,
            "requestedCount": count,
            "timeSeconds": round(elapsed_time, 2),
            "message": f"Successfully created {created_count} test todos with all fields in {elapsed_time:.2f}s"
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating test todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("API_PORT", "7071"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
