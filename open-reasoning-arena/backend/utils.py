import hashlib
import secrets
from passlib.context import CryptContext
from typing import Optional
from .models import Task, Solution, Score, Challenge, User
from .database import SessionLocal

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# Model fingerprinting
def generate_fingerprint(response: str) -> str:
    """Generate a fingerprint for a model's response to a secret prompt."""
    return hashlib.sha256(response.encode()).hexdigest()


def verify_model_fingerprint(model_name: str, response: str) -> bool:
    """Verify a model's fingerprint matches the expected response."""
    db = SessionLocal()
    try:
        fingerprint = generate_fingerprint(response)
        model_fp = db.query(ModelFingerprint).filter_by(model_name=model_name).first()
        if model_fp:
            return model_fp.fingerprint == fingerprint
        return False
    finally:
        db.close()


# Auto-scoring for objective tasks
def auto_score_solution(task: Task, solution: Solution) -> Optional[float]:
    """
    Auto-score a solution if the task is objective.
    Returns a score (0-100) or None if scoring fails.
    """
    if not task.is_objective or not task.expected_answer:
        return None
    
    # Simple exact match for now (can be enhanced with semantic similarity later)
    if solution.answer.strip().lower() == task.expected_answer.strip().lower():
        return 100.0
    else:
        return 0.0


# Reputation system
def update_reputation(user_id: int, points: int) -> None:
    """Update a user's reputation."""
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            user.reputation += points
            db.commit()
    finally:
        db.close()


def award_reputation_for_challenge(challenger_id: int) -> None:
    """Award reputation for a successful challenge."""
    update_reputation(challenger_id, 10)


def award_reputation_for_task_submission(author_id: int) -> None:
    """Award reputation for submitting a task."""
    update_reputation(author_id, 5)


def award_reputation_for_solution_submission(author_id: int) -> None:
    """Award reputation for submitting a solution."""
    update_reputation(author_id, 3)


def award_reputation_for_scoring(reviewer_id: int) -> None:
    """Award reputation for scoring a solution."""
    update_reputation(reviewer_id, 2)


# Secret prompt for model fingerprinting
SECRET_PROMPT = "Explain the concept of recursion in 3 sentences without using the word 'function'."
