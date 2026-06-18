"""
Open Reasoning Arena (ORA) - Main FastAPI Application.

This module provides the main FastAPI application with endpoints for:
- Users: User management and profiles
- Tasks: Reasoning tasks for models to solve
- Solutions: Model solutions to tasks
- Scores: Scoring of solutions
- Challenges: Adversarial challenges to solutions
- Leaderboard: Model performance rankings
- Model Fingerprints: Model verification

Security features:
- Rate limiting per endpoint type
- CORS restriction to configured origins
- Input validation with configurable limits
- Custom exception handling

Performance features:
- Caching for read operations (tasks, solutions, leaderboard)
- Database connection pooling
- OrderedDict-based LRU cache
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Any, Dict

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded as SlowapiRateLimitExceeded

from . import models, schemas, utils
from .database import get_db, engine, init_db
from .config import get_config, AppConfig
from .exceptions import (
    ORAError,
    NotFoundError,
    AlreadyExistsError,
    ValidationError,
    LengthValidationError,
    AuthenticationError,
    AuthorizationError,
    RateLimitExceededError,
    DatabaseError,
)
from .cache import (
    get_tasks_cache,
    get_solutions_cache,
    get_leaderboard_cache,
    clear_all_caches,
)
from .seed_tasks import SEED_TASKS
from .monitoring import (
    MonitoringMiddleware,
    init_monitoring,
    increment_task_created,
    increment_solution_created,
    increment_challenge_created,
    increment_challenge_accepted,
    increment_challenge_rejected,
    increment_score_created,
    increment_user_created,
    increment_error,
    increment_rate_limit,
    set_leaderboard_metrics,
)
from .logging_config import configure_logging, get_logger, LoggingMiddleware
from .api_docs import get_openapi_config, tags_metadata

# Configure structured logging
configure_logging()
logger = get_logger(__name__)

# Get the directory of this file
current_dir = __file__.rsplit("/", 1)[0] if "/" in __file__ else "."

# Set up templates
templates = Jinja2Templates(directory=f"{current_dir}/templates")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Get configuration
config = get_config()

# Create FastAPI app with enhanced OpenAPI config
openapi_config = get_openapi_config()
app = FastAPI(
    title=openapi_config["title"],
    description=openapi_config["description"],
    version=openapi_config["version"],
    debug=config.debug,
    openapi_tags=tags_metadata,
    contact=openapi_config.get("contact"),
    license_info=openapi_config.get("license"),
    servers=openapi_config.get("servers", []),
)

# Store config and limiter in app state
app.state.limiter = limiter
app.state.config = config

# Initialize monitoring
init_monitoring()

# Add middlewares
app.add_middleware(MonitoringMiddleware)
app.add_middleware(LoggingMiddleware)


# ==================== EXCEPTION HANDLERS ====================

@app.exception_handler(ORAError)
async def ora_error_handler(request: Request, exc: ORAError) -> JSONResponse:
    """Handle ORAError exceptions with consistent error format."""
    logger.warning(f"ORAError: {exc.code} - {exc.message}")
    # Track error in metrics
    endpoint = request.url.path.split("/")[1] if len(request.url.path.split("/")) > 1 else "root"
    increment_error(error_type=exc.code, endpoint=endpoint, status_code=str(exc.status_code))
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(exc.to_dict()),
    )


@app.exception_handler(SlowapiRateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: SlowapiRateLimitExceeded) -> JSONResponse:
    """Handle rate limit exceeded errors."""
    retry_after = int(exc.detail.get("retry-after", 60))
    logger.warning(f"Rate limit exceeded: {request.url} - Retry after: {retry_after}s")
    endpoint = request.url.path.split("/")[1] if len(request.url.path.split("/")) > 1 else "root"
    increment_rate_limit(endpoint=endpoint, limit_type="global")
    ora_exc = RateLimitExceededError(retry_after=retry_after)
    return JSONResponse(
        status_code=429,
        content=jsonable_encoder(ora_exc.to_dict()),
        headers={"Retry-After": str(retry_after)},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTPException with consistent error format."""
    logger.warning(f"HTTPException: {exc.status_code} - {exc.detail}")
    endpoint = request.url.path.split("/")[1] if len(request.url.path.split("/")) > 1 else "root"
    increment_error(error_type="HTTP_ERROR", endpoint=endpoint, status_code=str(exc.status_code))
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {type(exc).__name__}: {exc}", exc_info=True)
    endpoint = request.url.path.split("/")[1] if len(request.url.path.split("/")) > 1 else "root"
    increment_error(error_type=type(exc).__name__, endpoint=endpoint, status_code="500")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": str(exc) if config.debug else None,
        },
    )


# ==================== MIDDLEWARE ====================

# CORS middleware with configurable origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.cors_origins,
    allow_credentials=config.security.cors_allow_credentials,
    allow_methods=config.security.cors_allow_methods,
    allow_headers=config.security.cors_allow_headers,
)


# ==================== STARTUP EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Initialize database and seed initial data on startup."""
    logger.info("Starting Open Reasoning Arena...")
    
    # Initialize database tables
    try:
        init_db()
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise DatabaseError(message=str(e), operation="startup")
    
    # Seed initial data
    try:
        seed_initial_data()
        logger.info("Initial data seeded")
    except Exception as e:
        logger.error(f"Data seeding failed: {e}")
    
    logger.info(f"Open Reasoning Arena v{config.version} started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Shutting down Open Reasoning Arena...")
    clear_all_caches()
    logger.info("Caches cleared")


# ==================== STARTUP DATA SEEDING ====================

def seed_initial_data():
    """Seed initial tasks and default user if database is empty."""
    db = next(get_db())
    
    try:
        # Check if tasks already exist
        if not db.query(models.Task).first():
            # Create a default user for seeding
            db_user = models.User(
                username="ora_admin",
                email="admin@openreasoning.arena",
                is_human=True,
                reputation=100,
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            # Seed tasks
            for task_data in SEED_TASKS:
                db_task = models.Task(
                    title=task_data["title"],
                    description=task_data["description"],
                    category=task_data["category"],
                    difficulty=task_data["difficulty"],
                    is_objective=task_data["is_objective"],
                    expected_answer=task_data.get("expected_answer"),
                    author_id=db_user.id,
                )
                db.add(db_task)
            
            db.commit()
            logger.info(f"Seeded {len(SEED_TASKS)} tasks")
        
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# ==================== VALIDATION UTILITIES ====================

def validate_task_input(task: schemas.TaskCreate) -> None:
    """Validate task input against configuration limits."""
    if len(task.title) > config.security.max_task_title_length:
        raise LengthValidationError(
            field="title",
            value=task.title,
            max_length=config.security.max_task_title_length
        )
    if task.description and len(task.description) > config.security.max_task_description_length:
        raise LengthValidationError(
            field="description",
            value=task.description,
            max_length=config.security.max_task_description_length
        )


def validate_solution_input(solution: schemas.SolutionCreate) -> None:
    """Validate solution input against configuration limits."""
    if len(solution.answer) > config.security.max_solution_length:
        raise LengthValidationError(
            field="answer",
            value=solution.answer,
            max_length=config.security.max_solution_length
        )


def validate_challenge_input(challenge: schemas.ChallengeCreate) -> None:
    """Validate challenge input against configuration limits."""
    if len(challenge.counterexample) > config.security.max_challenge_length:
        raise LengthValidationError(
            field="counterexample",
            value=challenge.counterexample,
            max_length=config.security.max_challenge_length
        )


def validate_score_input(score: schemas.ScoreCreate) -> None:
    """Validate score input against configuration limits."""
    if score.feedback and len(score.feedback) > config.security.max_feedback_length:
        raise LengthValidationError(
            field="feedback",
            value=score.feedback,
            max_length=config.security.max_feedback_length
        )


# ==================== CACHE UTILITIES ====================

def get_cache_key(prefix: str, identifier: Any) -> str:
    """Generate a cache key for a given resource."""
    return f"{prefix}:{identifier}"


def cache_tasks_list(
    category: Optional[str] = None,
    difficulty: Optional[int] = None
) -> Optional[List[schemas.Task]]:
    """Get tasks from cache or return None if not cached."""
    cache = get_tasks_cache()
    cache_key = get_cache_key("tasks", f"{category}:{difficulty}")
    return cache.get(cache_key)


def set_cache_tasks_list(
    tasks: List[schemas.Task],
    category: Optional[str] = None,
    difficulty: Optional[int] = None
) -> None:
    """Cache tasks list."""
    cache = get_tasks_cache()
    cache_key = get_cache_key("tasks", f"{category}:{difficulty}")
    # Convert to dict for JSON serialization
    tasks_data = [task.model_dump() for task in tasks]
    cache.set(cache_key, tasks_data)


def cache_task(task: schemas.Task) -> None:
    """Cache a single task."""
    cache = get_tasks_cache()
    cache_key = get_cache_key("task", task.id)
    cache.set(cache_key, task.model_dump())


def get_cached_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Get a task from cache."""
    cache = get_tasks_cache()
    cache_key = get_cache_key("task", task_id)
    return cache.get(cache_key)


def cache_solutions_list(solutions: List[schemas.Solution], task_id: Optional[int] = None) -> None:
    """Cache solutions list."""
    cache = get_solutions_cache()
    cache_key = get_cache_key("solutions", f"task:{task_id}" if task_id else "all")
    solutions_data = [sol.model_dump() for sol in solutions]
    cache.set(cache_key, solutions_data)


def get_cached_solutions(task_id: Optional[int] = None) -> Optional[List[Dict[str, Any]]]:
    """Get solutions from cache."""
    cache = get_solutions_cache()
    cache_key = get_cache_key("solutions", f"task:{task_id}" if task_id else "all")
    return cache.get(cache_key)


def cache_leaderboard(leaderboard: schemas.LeaderboardResponse) -> None:
    """Cache leaderboard data."""
    cache = get_leaderboard_cache()
    cache_key = get_cache_key("leaderboard", "all")
    cache.set(cache_key, leaderboard.model_dump())


def get_cached_leaderboard() -> Optional[Dict[str, Any]]:
    """Get leaderboard from cache."""
    cache = get_leaderboard_cache()
    cache_key = get_cache_key("leaderboard", "all")
    return cache.get(cache_key)


# ==================== RATE LIMIT DECORATORS ====================

def get_tasks_limiter():
    """Get rate limiter for tasks endpoints."""
    return limiter.limit(config.security.rate_limit_tasks)


def get_solutions_limiter():
    """Get rate limiter for solutions endpoints."""
    return limiter.limit(config.security.rate_limit_solutions)


def get_challenges_limiter():
    """Get rate limiter for challenges endpoints."""
    return limiter.limit(config.security.rate_limit_challenges)


def get_scores_limiter():
    """Get rate limiter for scores endpoints."""
    return limiter.limit(config.security.rate_limit_solutions)  # Same as solutions


def get_leaderboard_limiter():
    """Get rate limiter for leaderboard endpoints."""
    return limiter.limit("10/minute")


# ==================== USER ENDPOINTS ====================

@app.post("/users/", response_model=schemas.User)
@limiter.limit(config.security.rate_limit)
async def create_user(
    request: Request,
    user: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user."""
    # Validate input
    if len(user.username) > 50:
        raise ValidationError(message="Username must be 50 characters or less", field="username")
    if len(user.email) > 255:
        raise ValidationError(message="Email must be 255 characters or less", field="email")
    
    # Check if username or email already exists
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if db_user:
        raise AlreadyExistsError(
            resource_type="User",
            field="username or email",
            value=user.username or user.email
        )
    
    # Hash password
    hashed_password = utils.get_password_hash(user.password)
    
    # Create user
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        is_human=user.is_human,
        reputation=0,
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Track metrics
    increment_user_created(is_human=user.is_human)
    
    return db_user


@app.get("/users/{user_id}", response_model=schemas.User)
@limiter.limit(config.security.rate_limit)
async def read_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get a user by ID."""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise NotFoundError(resource_type="User", resource_id=user_id)
    return db_user


# ==================== TASK ENDPOINTS ====================

@app.post("/tasks/", response_model=schemas.Task)
@limiter.limit(config.security.rate_limit_tasks)
async def create_task(
    request: Request,
    task: schemas.TaskCreate,
    db: Session = Depends(get_db)
):
    """Create a new task."""
    # Validate input
    validate_task_input(task)
    
    # TODO: Add authentication to get author_id
    # For MVP, use a default user (id=1)
    author_id = 1
    
    db_task = models.Task(
        title=task.title,
        description=task.description,
        category=task.category,
        difficulty=task.difficulty,
        is_objective=task.is_objective,
        expected_answer=task.expected_answer,
        author_id=author_id,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Award reputation for task submission
    utils.award_reputation_for_task_submission(author_id)
    
    # Track metrics
    increment_task_created(category=task.category, difficulty=task.difficulty)
    
    # Invalidate tasks cache
    get_tasks_cache().clear()
    
    return db_task


@app.get("/tasks/", response_model=List[schemas.Task])
@limiter.limit(config.security.rate_limit_tasks)
async def read_tasks(
    request: Request,
    category: Optional[str] = Query(None, max_length=50),
    difficulty: Optional[int] = Query(None, ge=1, le=5),
    db: Session = Depends(get_db)
):
    """Get all tasks with optional filtering."""
    # Try to get from cache first
    cache_key = get_cache_key("tasks", f"{category}:{difficulty}")
    cached = get_tasks_cache().get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit for tasks: {cache_key}")
        return [schemas.Task(**task) for task in cached]
    
    logger.debug(f"Cache miss for tasks: {cache_key}")
    
    # Query database
    query = db.query(models.Task)
    
    if category:
        query = query.filter(models.Task.category == category)
    if difficulty:
        query = query.filter(models.Task.difficulty == difficulty)
    
    tasks = query.all()
    
    # Cache the result
    set_cache_tasks_list(tasks, category, difficulty)
    
    return tasks


@app.get("/tasks/", response_class=HTMLResponse)
@limiter.limit(config.security.rate_limit_tasks)
async def read_tasks_html(
    request: Request,
    category: Optional[str] = Query(None, max_length=50),
    difficulty: Optional[int] = Query(None, ge=1, le=5),
    db: Session = Depends(get_db)
):
    """Get all tasks as HTML."""
    query = db.query(models.Task)
    
    if category:
        query = query.filter(models.Task.category == category)
    if difficulty:
        query = query.filter(models.Task.difficulty == difficulty)
    
    tasks = query.all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks})


@app.get("/tasks/{task_id}", response_model=schemas.Task)
@limiter.limit(config.security.rate_limit_tasks)
async def read_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get a task by ID."""
    # Try to get from cache first
    cached = get_cached_task(task_id)
    if cached is not None:
        logger.debug(f"Cache hit for task: {task_id}")
        return schemas.Task(**cached)
    
    logger.debug(f"Cache miss for task: {task_id}")
    
    # Query database
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise NotFoundError(resource_type="Task", resource_id=task_id)
    
    # Cache the result
    cache_task(db_task)
    
    return db_task


@app.get("/task/{task_id}", response_class=HTMLResponse)
@limiter.limit(config.security.rate_limit_tasks)
async def read_task_html(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get a task by ID as HTML."""
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise NotFoundError(resource_type="Task", resource_id=task_id)
    return templates.TemplateResponse("task_detail.html", {"request": request, "task": db_task})


# ==================== SOLUTION ENDPOINTS ====================

@app.post("/solutions/", response_model=schemas.Solution)
@limiter.limit(config.security.rate_limit_solutions)
async def create_solution(
    request: Request,
    solution: schemas.SolutionCreate,
    db: Session = Depends(get_db)
):
    """Create a new solution."""
    # Validate input
    validate_solution_input(solution)
    
    # TODO: Add authentication to get author_id
    # For MVP, use a default user (id=1)
    author_id = 1
    
    # Verify task exists
    db_task = db.query(models.Task).filter(models.Task.id == solution.task_id).first()
    if db_task is None:
        raise NotFoundError(resource_type="Task", resource_id=solution.task_id)
    
    # Create solution
    db_solution = models.Solution(
        task_id=solution.task_id,
        model_name=solution.model_name,
        answer=solution.answer,
        author_id=author_id,
    )
    db.add(db_solution)
    db.commit()
    db.refresh(db_solution)
    
    # Auto-score if task is objective
    if db_task.is_objective:
        score = utils.auto_score_solution(db_task, db_solution)
        if score is not None:
            db_score = models.Score(
                solution_id=db_solution.id,
                reviewer_id=1,  # System user for auto-scoring
                score=score,
                is_automated=True,
            )
            db.add(db_score)
            db.commit()
    
    # Award reputation for solution submission
    utils.award_reputation_for_solution_submission(author_id)
    
    # Track metrics
    increment_solution_created(model_name=solution.model_name)
    
    # Invalidate caches
    get_solutions_cache().clear()
    get_leaderboard_cache().clear()
    
    return db_solution


@app.get("/solutions/{solution_id}", response_model=schemas.Solution)
@limiter.limit(config.security.rate_limit_solutions)
async def read_solution(
    request: Request,
    solution_id: int,
    db: Session = Depends(get_db)
):
    """Get a solution by ID."""
    db_solution = db.query(models.Solution).filter(models.Solution.id == solution_id).first()
    if db_solution is None:
        raise NotFoundError(resource_type="Solution", resource_id=solution_id)
    return db_solution


@app.get("/tasks/{task_id}/solutions", response_model=List[schemas.Solution])
@limiter.limit(config.security.rate_limit_solutions)
async def read_solutions_for_task(
    request: Request,
    task_id: int,
    db: Session = Depends(get_db)
):
    """Get all solutions for a task."""
    # Verify task exists
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise NotFoundError(resource_type="Task", resource_id=task_id)
    
    # Try to get from cache first
    cached = get_cached_solutions(task_id)
    if cached is not None:
        logger.debug(f"Cache hit for solutions: task:{task_id}")
        return [schemas.Solution(**sol) for sol in cached]
    
    logger.debug(f"Cache miss for solutions: task:{task_id}")
    
    # Query database
    solutions = db.query(models.Solution).filter(models.Solution.task_id == task_id).all()
    
    # Cache the result
    cache_solutions_list(solutions, task_id)
    
    return solutions


# ==================== SCORE ENDPOINTS ====================

@app.post("/scores/", response_model=schemas.Score)
@limiter.limit(config.security.rate_limit_solutions)
async def create_score(
    request: Request,
    score: schemas.ScoreCreate,
    db: Session = Depends(get_db)
):
    """Create a new score."""
    # Validate input
    validate_score_input(score)
    
    # TODO: Add authentication to get reviewer_id
    # For MVP, use a default user (id=1)
    reviewer_id = 1
    
    # Verify solution exists
    db_solution = db.query(models.Solution).filter(models.Solution.id == score.solution_id).first()
    if db_solution is None:
        raise NotFoundError(resource_type="Solution", resource_id=score.solution_id)
    
    # Create score
    db_score = models.Score(
        solution_id=score.solution_id,
        reviewer_id=reviewer_id,
        score=score.score,
        feedback=score.feedback,
        is_automated=score.is_automated,
    )
    db.add(db_score)
    db.commit()
    db.refresh(db_score)
    
    # Award reputation for scoring
    utils.award_reputation_for_scoring(reviewer_id)
    
    # Track metrics
    increment_score_created()
    
    # Invalidate caches
    get_leaderboard_cache().clear()
    
    return db_score


@app.get("/solutions/{solution_id}/scores", response_model=List[schemas.Score])
@limiter.limit(config.security.rate_limit_solutions)
async def read_scores_for_solution(
    request: Request,
    solution_id: int,
    db: Session = Depends(get_db)
):
    """Get all scores for a solution."""
    db_solution = db.query(models.Solution).filter(models.Solution.id == solution_id).first()
    if db_solution is None:
        raise NotFoundError(resource_type="Solution", resource_id=solution_id)
    
    scores = db.query(models.Score).filter(models.Score.solution_id == solution_id).all()
    return scores


# ==================== CHALLENGE ENDPOINTS ====================

@app.post("/challenges/", response_model=schemas.Challenge)
@limiter.limit(config.security.rate_limit_challenges)
async def create_challenge(
    request: Request,
    challenge: schemas.ChallengeCreate,
    db: Session = Depends(get_db)
):
    """Create a new challenge."""
    # Validate input
    validate_challenge_input(challenge)
    
    # TODO: Add authentication to get challenger_id
    # For MVP, use a default user (id=1)
    challenger_id = 1
    
    # Verify solution exists
    db_solution = db.query(models.Solution).filter(models.Solution.id == challenge.solution_id).first()
    if db_solution is None:
        raise NotFoundError(resource_type="Solution", resource_id=challenge.solution_id)
    
    # Create challenge
    db_challenge = models.Challenge(
        solution_id=challenge.solution_id,
        challenger_id=challenger_id,
        counterexample=challenge.counterexample,
        status="pending",
    )
    db.add(db_challenge)
    db.commit()
    db.refresh(db_challenge)
    
    # Award reputation for challenge
    utils.award_reputation_for_challenge(challenger_id)
    
    # Track metrics
    increment_challenge_created()
    
    return db_challenge


@app.get("/challenges/", response_model=List[schemas.Challenge])
@limiter.limit(config.security.rate_limit_challenges)
async def read_challenges(
    request: Request,
    solution_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all challenges with optional filtering."""
    query = db.query(models.Challenge)
    
    if solution_id:
        query = query.filter(models.Challenge.solution_id == solution_id)
    
    challenges = query.all()
    return challenges


@app.post("/challenges/{challenge_id}/accept")
@limiter.limit(config.security.rate_limit_challenges)
async def accept_challenge(
    request: Request,
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """Accept a challenge."""
    db_challenge = db.query(models.Challenge).filter(models.Challenge.id == challenge_id).first()
    if db_challenge is None:
        raise NotFoundError(resource_type="Challenge", resource_id=challenge_id)
    
    db_challenge.status = "accepted"
    db_challenge.resolved_at = datetime.utcnow()
    db.commit()
    
    # TODO: Invalidate the solution's scores or mark it as "broken"
    
    # Award reputation for accepted challenge
    utils.award_reputation_for_challenge_accepted(db_challenge.challenger_id)
    
    # Track metrics
    increment_challenge_accepted()
    
    return {"message": "Challenge accepted"}


@app.post("/challenges/{challenge_id}/reject")
@limiter.limit(config.security.rate_limit_challenges)
async def reject_challenge(
    request: Request,
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """Reject a challenge."""
    db_challenge = db.query(models.Challenge).filter(models.Challenge.id == challenge_id).first()
    if db_challenge is None:
        raise NotFoundError(resource_type="Challenge", resource_id=challenge_id)
    
    db_challenge.status = "rejected"
    db_challenge.resolved_at = datetime.utcnow()
    db.commit()
    
    # Track metrics
    increment_challenge_rejected()
    
    return {"message": "Challenge rejected"}


# ==================== LEADERBOARD ENDPOINTS ====================

@app.get("/leaderboard/", response_model=schemas.LeaderboardResponse)
@limiter.limit("10/minute")
async def get_leaderboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get the leaderboard with model rankings."""
    # Try to get from cache first
    cached = get_cached_leaderboard()
    if cached is not None:
        logger.debug("Cache hit for leaderboard")
        return schemas.LeaderboardResponse(**cached)
    
    logger.debug("Cache miss for leaderboard")
    
    # Query all solutions and their scores
    solutions = db.query(models.Solution).all()
    
    # Group by model_name and calculate avg score and tasks solved
    model_stats = {}
    for solution in solutions:
        model_name = solution.model_name
        if model_name not in model_stats:
            model_stats[model_name] = {
                "total_score": 0,
                "num_scores": 0,
                "tasks_solved": set(),
                "total_submissions": 0,
            }
        
        # Count submissions
        model_stats[model_name]["total_submissions"] += 1
        
        # Get scores for this solution
        scores = db.query(models.Score).filter(models.Score.solution_id == solution.id).all()
        if scores:
            model_stats[model_name]["num_scores"] += len(scores)
            model_stats[model_name]["total_score"] += sum(score.score for score in scores)
            model_stats[model_name]["tasks_solved"].add(solution.task_id)
    
    # Calculate averages
    leaderboard = []
    for model_name, stats in model_stats.items():
        avg_score = (stats["total_score"] / stats["num_scores"]) if stats["num_scores"] > 0 else 0
        leaderboard.append({
            "model_name": model_name,
            "avg_score": avg_score,
            "tasks_solved": len(stats["tasks_solved"]),
            "total_submissions": stats["total_submissions"],
        })
    
    # Sort by avg_score descending
    leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
    
    result = schemas.LeaderboardResponse(models=leaderboard)
    
    # Set leaderboard metrics
    if leaderboard:
        set_leaderboard_metrics(
            models_count=len(leaderboard),
            top_score=leaderboard[0]["avg_score"] if leaderboard else 0
        )
    
    # Cache the result
    cache_leaderboard(result)
    
    return result


@app.get("/leaderboard/", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def get_leaderboard_html(
    request: Request,
    db: Session = Depends(get_db)
):
    """Get the leaderboard as HTML."""
    # Try to get from cache first
    cached = get_cached_leaderboard()
    if cached is not None:
        logger.debug("Cache hit for leaderboard HTML")
        leaderboard_data = schemas.LeaderboardResponse(**cached)
        return templates.TemplateResponse("leaderboard.html", {
            "request": request,
            "models": leaderboard_data.models
        })
    
    logger.debug("Cache miss for leaderboard HTML")
    
    # Query all solutions and their scores
    solutions = db.query(models.Solution).all()
    
    # Group by model_name and calculate avg score and tasks solved
    model_stats = {}
    for solution in solutions:
        model_name = solution.model_name
        if model_name not in model_stats:
            model_stats[model_name] = {
                "total_score": 0,
                "num_scores": 0,
                "tasks_solved": set(),
                "total_submissions": 0,
            }
        
        # Count submissions
        model_stats[model_name]["total_submissions"] += 1
        
        # Get scores for this solution
        scores = db.query(models.Score).filter(models.Score.solution_id == solution.id).all()
        if scores:
            model_stats[model_name]["num_scores"] += len(scores)
            model_stats[model_name]["total_score"] += sum(score.score for score in scores)
            model_stats[model_name]["tasks_solved"].add(solution.task_id)
    
    # Calculate averages
    leaderboard = []
    for model_name, stats in model_stats.items():
        avg_score = (stats["total_score"] / stats["num_scores"]) if stats["num_scores"] > 0 else 0
        leaderboard.append({
            "model_name": model_name,
            "avg_score": avg_score,
            "tasks_solved": len(stats["tasks_solved"]),
            "total_submissions": stats["total_submissions"],
        })
    
    # Sort by avg_score descending
    leaderboard.sort(key=lambda x: x["avg_score"], reverse=True)
    
    return templates.TemplateResponse("leaderboard.html", {"request": request, "models": leaderboard})


# ==================== MODEL FINGERPRINT ENDPOINTS ====================

@app.post("/fingerprints/", response_model=schemas.ModelFingerprint)
@limiter.limit(config.security.rate_limit)
async def create_fingerprint(
    request: Request,
    fingerprint: schemas.ModelFingerprintCreate,
    db: Session = Depends(get_db)
):
    """Create a new model fingerprint."""
    # Validate input
    if len(fingerprint.model_name) > 100:
        raise LengthValidationError(
            field="model_name",
            value=fingerprint.model_name,
            max_length=100
        )
    if len(fingerprint.fingerprint) > 64:
        raise LengthValidationError(
            field="fingerprint",
            value=fingerprint.fingerprint,
            max_length=64
        )
    
    # TODO: Add authentication to get owner_id
    # For MVP, use a default user (id=1)
    owner_id = 1
    
    db_fingerprint = models.ModelFingerprint(
        model_name=fingerprint.model_name,
        fingerprint=fingerprint.fingerprint,
        owner_id=owner_id,
    )
    db.add(db_fingerprint)
    db.commit()
    db.refresh(db_fingerprint)
    
    return db_fingerprint


@app.get("/fingerprints/{model_name}", response_model=schemas.ModelFingerprint)
@limiter.limit(config.security.rate_limit)
async def read_fingerprint(
    request: Request,
    model_name: str,
    db: Session = Depends(get_db)
):
    """Get a model fingerprint by model name."""
    db_fingerprint = db.query(models.ModelFingerprint).filter(
        models.ModelFingerprint.model_name == model_name
    ).first()
    if db_fingerprint is None:
        raise NotFoundError(resource_type="ModelFingerprint", resource_id=model_name)
    return db_fingerprint


# ==================== HEALTH CHECK ====================

@app.get("/")
@limiter.exempt
async def read_root():
    """Root endpoint with basic info."""
    return {
        "name": config.name,
        "version": config.version,
        "description": "A dynamic, adversarial benchmark for LLM reasoning.",
        "docs": "/docs",
    }


@app.get("/health")
@limiter.exempt
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Get cache stats
    tasks_cache = get_tasks_cache()
    solutions_cache = get_solutions_cache()
    leaderboard_cache = get_leaderboard_cache()
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "cache": {
            "tasks": tasks_cache.get_stats().to_dict(),
            "solutions": solutions_cache.get_stats().to_dict(),
            "leaderboard": leaderboard_cache.get_stats().to_dict(),
        },
        "version": config.version,
        "environment": config.environment,
    }


# ==================== STATIC FILES ====================

# Mount static files
app.mount("/static", StaticFiles(directory=f"{current_dir}/static"), name="static")
