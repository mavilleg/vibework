from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    is_human = Column(Boolean, default=True)  # True = human, False = model
    reputation = Column(Integer, default=0)  # Reputation score for contributions
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    tasks = relationship("Task", back_populates="author")
    solutions = relationship("Solution", back_populates="author")
    scores = relationship("Score", back_populates="reviewer")
    challenges = relationship("Challenge", back_populates="challenger")


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    category = Column(String, index=True)  # e.g., "math", "logic", "code"
    difficulty = Column(Integer)  # 1-5
    is_objective = Column(Boolean, default=False)  # Can be auto-scored
    expected_answer = Column(Text)  # For objective tasks
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    author = relationship("User", back_populates="tasks")
    solutions = relationship("Solution", back_populates="task")


class Solution(Base):
    __tablename__ = "solutions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    model_name = Column(String)  # e.g., "gpt-4", "llama-3-70b"
    answer = Column(Text)
    author_id = Column(Integer, ForeignKey("users.id"))  # User who submitted the solution
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    task = relationship("Task", back_populates="solutions")
    author = relationship("User", back_populates="solutions")
    scores = relationship("Score", back_populates="solution")
    challenges = relationship("Challenge", back_populates="solution")


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    solution_id = Column(Integer, ForeignKey("solutions.id"))
    reviewer_id = Column(Integer, ForeignKey("users.id"))  # Human or model reviewer
    score = Column(Float)  # 0-100
    feedback = Column(Text)
    is_automated = Column(Boolean, default=False)  # True if scored by a script
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    solution = relationship("Solution", back_populates="scores")
    reviewer = relationship("User", back_populates="scores")


class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(Integer, primary_key=True, index=True)
    solution_id = Column(Integer, ForeignKey("solutions.id"))
    challenger_id = Column(Integer, ForeignKey("users.id"))  # User who submitted the challenge
    counterexample = Column(Text)  # The counterexample that breaks the solution
    status = Column(String, default="pending")  # "pending", "accepted", "rejected"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    solution = relationship("Solution", back_populates="challenges")
    challenger = relationship("User", back_populates="challenges")


class ModelFingerprint(Base):
    __tablename__ = "model_fingerprints"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, unique=True, index=True)
    fingerprint = Column(String)  # Hash of the model's response to a secret prompt
    owner_id = Column(Integer, ForeignKey("users.id"))  # User who registered the model
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    owner = relationship("User")
