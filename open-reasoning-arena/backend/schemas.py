from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_human: bool = True


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    reputation: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Task Schemas
class TaskBase(BaseModel):
    title: str
    description: str
    category: str
    difficulty: int = Field(ge=1, le=5)
    is_objective: bool = False
    expected_answer: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class Task(TaskBase):
    id: int
    author_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Solution Schemas
class SolutionBase(BaseModel):
    task_id: int
    model_name: str
    answer: str


class SolutionCreate(SolutionBase):
    pass


class Solution(SolutionBase):
    id: int
    author_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Score Schemas
class ScoreBase(BaseModel):
    solution_id: int
    score: float = Field(ge=0, le=100)
    feedback: Optional[str] = None
    is_automated: bool = False


class ScoreCreate(ScoreBase):
    pass


class Score(ScoreBase):
    id: int
    reviewer_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Challenge Schemas
class ChallengeBase(BaseModel):
    solution_id: int
    counterexample: str


class ChallengeCreate(ChallengeBase):
    pass


class Challenge(ChallengeBase):
    id: int
    challenger_id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# Model Fingerprint Schemas
class ModelFingerprintBase(BaseModel):
    model_name: str
    fingerprint: str


class ModelFingerprintCreate(ModelFingerprintBase):
    pass


class ModelFingerprint(ModelFingerprintBase):
    id: int
    owner_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Leaderboard Schemas
class ModelPerformance(BaseModel):
    model_name: str
    avg_score: float
    tasks_solved: int
    total_submissions: int
    
    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    models: List[ModelPerformance]
