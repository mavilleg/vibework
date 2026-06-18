from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, Float, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Null for models
    is_human = Column(Boolean, default=True, nullable=False)  # True = human, False = model
    reputation = Column(Integer, default=0, nullable=False)  # Reputation score for contributions
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    roles = Column(JSON, default=["user"], nullable=False)  # List of roles: user, moderator, admin
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_users_username', 'username'),
        Index('ix_users_email', 'email'),
        Index('ix_users_reputation', 'reputation'),
        Index('ix_users_active', 'is_active'),
        Index('ix_users_created', 'created_at'),
    )
    
    # Relationships
    tasks = relationship("Task", back_populates="author", cascade="all, delete-orphan")
    solutions = relationship("Solution", back_populates="author", cascade="all, delete-orphan")
    scores = relationship("Score", back_populates="reviewer", cascade="all, delete-orphan")
    challenges = relationship("Challenge", back_populates="challenger", cascade="all, delete-orphan", foreign_keys="Challenge.challenger_id")
    resolved_challenges = relationship("Challenge", back_populates="resolver", cascade="all, delete-orphan", foreign_keys="Challenge.resolved_by")
    fingerprints = relationship("ModelFingerprint", back_populates="owner", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', reputation={self.reputation}, roles={self.roles})>"
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.is_superuser or (self.roles and "admin" in self.roles)
    
    @property
    def is_moderator(self) -> bool:
        """Check if user is a moderator."""
        return self.is_admin or (self.roles and "moderator" in self.roles)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), index=True, nullable=False)  # e.g., "math", "logic", "code"
    difficulty = Column(Integer, nullable=False)  # 1-5
    is_objective = Column(Boolean, default=False, nullable=False)  # Can be auto-scored
    expected_answer = Column(Text, nullable=True)  # For objective tasks
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_approved = Column(Boolean, default=True, nullable=False)
    view_count = Column(Integer, default=0, nullable=False)
    solution_count = Column(Integer, default=0, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_tasks_category', 'category'),
        Index('ix_tasks_difficulty', 'difficulty'),
        Index('ix_tasks_author', 'author_id'),
        Index('ix_tasks_created', 'created_at'),
    )
    
    # Relationships
    author = relationship("User", back_populates="tasks")
    solutions = relationship("Solution", back_populates="task", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Task(id={self.id}, title='{self.title[:30]}...', category='{self.category}')>"


class Solution(Base):
    __tablename__ = "solutions"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    model_name = Column(String(100), nullable=False)  # e.g., "gpt-4", "llama-3-70b"
    answer = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who submitted the solution
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(100), nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_solutions_task', 'task_id'),
        Index('ix_solutions_model', 'model_name'),
        Index('ix_solutions_author', 'author_id'),
        Index('ix_solutions_created', 'created_at'),
    )
    
    # Relationships
    task = relationship("Task", back_populates="solutions")
    author = relationship("User", back_populates="solutions")
    scores = relationship("Score", back_populates="solution", cascade="all, delete-orphan")
    challenges = relationship("Challenge", back_populates="solution", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Solution(id={self.id}, task_id={self.task_id}, model='{self.model_name}')>"


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    solution_id = Column(Integer, ForeignKey("solutions.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Human or model reviewer
    score = Column(Float, nullable=False)  # 0-100
    feedback = Column(Text, nullable=True)
    is_automated = Column(Boolean, default=False, nullable=False)  # True if scored by a script
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_scores_solution', 'solution_id'),
        Index('ix_scores_reviewer', 'reviewer_id'),
        Index('ix_scores_created', 'created_at'),
    )
    
    # Relationships
    solution = relationship("Solution", back_populates="scores")
    reviewer = relationship("User", back_populates="scores")
    
    def __repr__(self):
        return f"<Score(id={self.id}, solution_id={self.solution_id}, score={self.score})>"


class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(Integer, primary_key=True, index=True)
    solution_id = Column(Integer, ForeignKey("solutions.id"), nullable=False)
    challenger_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who submitted the challenge
    counterexample = Column(Text, nullable=False)  # The counterexample that breaks the solution
    status = Column(String(20), default="pending", nullable=False)  # "pending", "accepted", "rejected"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_challenges_solution', 'solution_id'),
        Index('ix_challenges_challenger', 'challenger_id'),
        Index('ix_challenges_status', 'status'),
        Index('ix_challenges_created', 'created_at'),
    )
    
    # Relationships
    solution = relationship("Solution", back_populates="challenges")
    challenger = relationship("User", back_populates="challenges", foreign_keys=[challenger_id])
    resolver = relationship("User", back_populates="challenges", foreign_keys=[resolved_by])
    
    def __repr__(self):
        return f"<Challenge(id={self.id}, solution_id={self.solution_id}, status='{self.status}')>"


class ModelFingerprint(Base):
    __tablename__ = "model_fingerprints"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), unique=True, index=True, nullable=False)
    fingerprint = Column(String(64), nullable=False)  # SHA-256 hash of the model's response to a secret prompt
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User who registered the model
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_attempts = Column(Integer, default=0, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_fingerprints_model', 'model_name'),
        Index('ix_fingerprints_owner', 'owner_id'),
    )
    
    # Relationships
    owner = relationship("User", back_populates="fingerprints")
    
    def __repr__(self):
        return f"<ModelFingerprint(id={self.id}, model='{self.model_name}', verified={self.is_verified})>"
