"""
Configuration management for Open Reasoning Arena.

This module provides centralized configuration with environment variable support
and sensible defaults for development and production environments.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / ".env")


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    url: str = os.getenv("DATABASE_URL", "sqlite:///./ora.db")
    echo: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", "5"))
    max_overflow: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
    
    def get_sqlalchemy_url(self) -> str:
        """Get SQLAlchemy-compatible database URL."""
        # For SQLite, ensure proper path
        if self.url.startswith("sqlite:///"):
            # Convert to absolute path if relative
            if not self.url.startswith("sqlite:////"):
                # Relative path - make it absolute
                db_path = self.url.replace("sqlite:///", "")
                abs_path = str(Path(__file__).parent / db_path)
                return f"sqlite:///{abs_path}"
        return self.url


@dataclass
class SecurityConfig:
    """Security configuration."""
    
    # Rate limiting
    rate_limit: str = os.getenv("RATE_LIMIT", "100/minute")
    rate_limit_tasks: str = os.getenv("RATE_LIMIT_TASKS", "30/minute")
    rate_limit_solutions: str = os.getenv("RATE_LIMIT_SOLUTIONS", "20/minute")
    rate_limit_challenges: str = os.getenv("RATE_LIMIT_CHALLENGES", "15/minute")
    
    # JWT Authentication
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    enable_auth: bool = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    
    # Legacy secret key for backward compatibility
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    
    # CORS
    cors_origins: List[str] = field(default_factory=lambda: 
        os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = field(default_factory=lambda: 
        os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    )
    cors_allow_headers: List[str] = field(default_factory=lambda: 
        os.getenv("CORS_HEADERS", "Authorization,Content-Type").split(",")
    )
    
    # Input validation
    max_task_title_length: int = int(os.getenv("MAX_TASK_TITLE_LENGTH", "200"))
    max_task_description_length: int = int(os.getenv("MAX_TASK_DESCRIPTION_LENGTH", "5000"))
    max_solution_length: int = int(os.getenv("MAX_SOLUTION_LENGTH", "10000"))
    max_challenge_length: int = int(os.getenv("MAX_CHALLENGE_LENGTH", "5000"))
    max_feedback_length: int = int(os.getenv("MAX_FEEDBACK_LENGTH", "2000"))
    
    def validate(self) -> None:
        """Validate security configuration."""
        if self.access_token_expire_minutes <= 0:
            raise ValueError("Access token expire minutes must be positive")
        if self.max_task_title_length <= 0:
            raise ValueError("Max task title length must be positive")
        if self.max_task_description_length <= 0:
            raise ValueError("Max task description length must be positive")


@dataclass
class CacheConfig:
    """Cache configuration."""
    
    enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    ttl: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour
    max_size: int = int(os.getenv("CACHE_MAX_SIZE", "1000"))
    backend: str = os.getenv("CACHE_BACKEND", "memory")  # memory, redis
    
    # Redis configuration
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    redis_pool_size: int = int(os.getenv("REDIS_POOL_SIZE", "10"))
    
    def validate(self) -> None:
        """Validate cache configuration."""
        if self.ttl <= 0:
            raise ValueError("Cache TTL must be positive")
        if self.max_size <= 0:
            raise ValueError("Cache max size must be positive")
        if self.backend not in ["memory", "redis"]:
            raise ValueError(f"Invalid cache backend: {self.backend}")
        if self.backend == "redis":
            if self.redis_pool_size <= 0:
                raise ValueError("Redis pool size must be positive")


@dataclass
class ReputationConfig:
    """Reputation system configuration."""
    
    task_submission: int = int(os.getenv("REP_TASK_SUBMISSION", "5"))
    solution_submission: int = int(os.getenv("REP_SOLUTION_SUBMISSION", "3"))
    challenge_submission: int = int(os.getenv("REP_CHALLENGE_SUBMISSION", "10"))
    challenge_accepted: int = int(os.getenv("REP_CHALLENGE_ACCEPTED", "15"))
    scoring: int = int(os.getenv("REP_SCORING", "2"))
    solution_accepted: int = int(os.getenv("REP_SOLUTION_ACCEPTED", "5"))
    
    def validate(self) -> None:
        """Validate reputation configuration."""
        if any(value < 0 for value in [
            self.task_submission, self.solution_submission, self.challenge_submission,
            self.challenge_accepted, self.scoring, self.solution_accepted
        ]):
            raise ValueError("Reputation values must be non-negative")


@dataclass
class AppConfig:
    """Main application configuration."""
    
    name: str = os.getenv("APP_NAME", "Open Reasoning Arena")
    version: str = os.getenv("APP_VERSION", "0.1.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    port: int = int(os.getenv("PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    reputation: ReputationConfig = field(default_factory=ReputationConfig)
    
    def validate(self) -> None:
        """Validate the entire configuration."""
        self.security.validate()
        self.cache.validate()
        self.reputation.validate()
        
        if self.port < 1 or self.port > 65535:
            raise ValueError("Port must be between 1 and 65535")
        
        if self.environment not in ["development", "staging", "production"]:
            raise ValueError(f"Invalid environment: {self.environment}")


# Global configuration instance
config = AppConfig()

# Validate configuration on import
try:
    config.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    # Continue with defaults in development
    if config.environment != "production":
        print("Using default configuration for development")


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config


def reload_config() -> AppConfig:
    """Reload configuration from environment variables."""
    global config
    config = AppConfig()
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
    return config
