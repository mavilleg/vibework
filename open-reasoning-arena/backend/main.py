from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os

from . import models, schemas, utils
from .database import get_db, engine
from .seed_tasks import SEED_TASKS

# Get the directory of this file
current_dir = os.path.dirname(os.path.abspath(__file__))

# Set up templates
templates = Jinja2Templates(directory=os.path.join(current_dir, "templates"))

# Create tables on startup
models.Base.metadata.create_all(bind=engine)

# Seed initial data
@app.on_event("startup")
def seed_initial_data():
    db = next(get_db())
    
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
    
    db.close()

app = FastAPI(
    title="Open Reasoning Arena (ORA)",
    description="A dynamic, adversarial benchmark for LLM reasoning.",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== USER ENDPOINTS ====================

@app.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if username or email already exists
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    # Hash password
    hashed_password = utils.get_password_hash(user.password)
    
    # Create user
    db_user = models.User(
        username=user.username,
        email=user.email,
        is_human=user.is_human,
        reputation=0,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


# ==================== TASK ENDPOINTS ====================

@app.post("/tasks/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
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
    
    return db_task


@app.get("/tasks/", response_model=List[schemas.Task])
def read_tasks(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Task)
    
    if category:
        query = query.filter(models.Task.category == category)
    if difficulty:
        query = query.filter(models.Task.difficulty == difficulty)
    
    tasks = query.all()
    return tasks


@app.get("/tasks/", response_class=HTMLResponse)
def read_tasks_html(
    request: Request,
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Task)
    
    if category:
        query = query.filter(models.Task.category == category)
    if difficulty:
        query = query.filter(models.Task.difficulty == difficulty)
    
    tasks = query.all()
    return templates.TemplateResponse("tasks.html", {"request": request, "tasks": tasks})


@app.get("/tasks/{task_id}", response_model=schemas.Task)
def read_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return db_task


@app.get("/task/{task_id}", response_class=HTMLResponse)
def read_task_html(request: Request, task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return templates.TemplateResponse("task_detail.html", {"request": request, "task": db_task})


# ==================== SOLUTION ENDPOINTS ====================

@app.post("/solutions/", response_model=schemas.Solution)
def create_solution(solution: schemas.SolutionCreate, db: Session = Depends(get_db)):
    # TODO: Add authentication to get author_id
    # For MVP, use a default user (id=1)
    author_id = 1
    
    # Verify task exists
    db_task = db.query(models.Task).filter(models.Task.id == solution.task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
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
    
    return db_solution


@app.get("/solutions/{solution_id}", response_model=schemas.Solution)
def read_solution(solution_id: int, db: Session = Depends(get_db)):
    db_solution = db.query(models.Solution).filter(models.Solution.id == solution_id).first()
    if db_solution is None:
        raise HTTPException(status_code=404, detail="Solution not found")
    return db_solution


@app.get("/tasks/{task_id}/solutions", response_model=List[schemas.Solution])
def read_solutions_for_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    solutions = db.query(models.Solution).filter(models.Solution.task_id == task_id).all()
    return solutions


# ==================== SCORE ENDPOINTS ====================

@app.post("/scores/", response_model=schemas.Score)
def create_score(score: schemas.ScoreCreate, db: Session = Depends(get_db)):
    # TODO: Add authentication to get reviewer_id
    # For MVP, use a default user (id=1)
    reviewer_id = 1
    
    # Verify solution exists
    db_solution = db.query(models.Solution).filter(models.Solution.id == score.solution_id).first()
    if db_solution is None:
        raise HTTPException(status_code=404, detail="Solution not found")
    
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
    
    return db_score


@app.get("/solutions/{solution_id}/scores", response_model=List[schemas.Score])
def read_scores_for_solution(solution_id: int, db: Session = Depends(get_db)):
    db_solution = db.query(models.Solution).filter(models.Solution.id == solution_id).first()
    if db_solution is None:
        raise HTTPException(status_code=404, detail="Solution not found")
    
    scores = db.query(models.Score).filter(models.Score.solution_id == solution_id).all()
    return scores


# ==================== CHALLENGE ENDPOINTS ====================

@app.post("/challenges/", response_model=schemas.Challenge)
def create_challenge(challenge: schemas.ChallengeCreate, db: Session = Depends(get_db)):
    # TODO: Add authentication to get challenger_id
    # For MVP, use a default user (id=1)
    challenger_id = 1
    
    # Verify solution exists
    db_solution = db.query(models.Solution).filter(models.Solution.id == challenge.solution_id).first()
    if db_solution is None:
        raise HTTPException(status_code=404, detail="Solution not found")
    
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
    
    return db_challenge


@app.get("/challenges/", response_model=List[schemas.Challenge])
def read_challenges(solution_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Challenge)
    
    if solution_id:
        query = query.filter(models.Challenge.solution_id == solution_id)
    
    challenges = query.all()
    return challenges


@app.post("/challenges/{challenge_id}/accept")
def accept_challenge(challenge_id: int, db: Session = Depends(get_db)):
    db_challenge = db.query(models.Challenge).filter(models.Challenge.id == challenge_id).first()
    if db_challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    db_challenge.status = "accepted"
    db.commit()
    
    # TODO: Invalidate the solution's scores or mark it as "broken"
    
    return {"message": "Challenge accepted"}


@app.post("/challenges/{challenge_id}/reject")
def reject_challenge(challenge_id: int, db: Session = Depends(get_db)):
    db_challenge = db.query(models.Challenge).filter(models.Challenge.id == challenge_id).first()
    if db_challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    db_challenge.status = "rejected"
    db.commit()
    
    return {"message": "Challenge rejected"}


# ==================== LEADERBOARD ENDPOINTS ====================

@app.get("/leaderboard/", response_model=schemas.LeaderboardResponse)
def get_leaderboard(db: Session = Depends(get_db)):
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
    
    return {"models": leaderboard}


@app.get("/leaderboard/", response_class=HTMLResponse)
def get_leaderboard_html(request: Request, db: Session = Depends(get_db)):
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
def create_fingerprint(fingerprint: schemas.ModelFingerprintCreate, db: Session = Depends(get_db)):
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
def read_fingerprint(model_name: str, db: Session = Depends(get_db)):
    db_fingerprint = db.query(models.ModelFingerprint).filter(
        models.ModelFingerprint.model_name == model_name
    ).first()
    if db_fingerprint is None:
        raise HTTPException(status_code=404, detail="Model fingerprint not found")
    return db_fingerprint


# ==================== HEALTH CHECK ====================

@app.get("/")
def read_root():
    return {
        "name": "Open Reasoning Arena (ORA)",
        "version": "0.1.0",
        "description": "A dynamic, adversarial benchmark for LLM reasoning.",
        "docs": "/docs",
    }
