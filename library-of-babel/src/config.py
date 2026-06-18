"""
Configuration management for the Library of Babel project.

This module provides centralized configuration with environment variable support
and sensible defaults for development and production environments.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")


@dataclass
class AzureConfig:
    """Azure-specific configuration."""
    
    storage_connection_string: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    redis_connection_string: Optional[str] = os.getenv("AZURE_REDIS_CONNECTION_STRING")
    blob_container: str = os.getenv("AZURE_BLOB_CONTAINER", "books")
    app_service_name: Optional[str] = os.getenv("AZURE_APP_SERVICE_NAME")
    resource_group: Optional[str] = os.getenv("AZURE_RESOURCE_GROUP")
    subscription_id: Optional[str] = os.getenv("AZURE_SUBSCRIPTION_ID")
    
    @property
    def is_azure_enabled(self) -> bool:
        """Check if Azure services are configured."""
        return (
            self.storage_connection_string is not None or
            self.redis_connection_string is not None
        )


@dataclass
class BookConfig:
    """Configuration for book generation."""
    
    pages: int = int(os.getenv("BOOK_PAGES", "410"))
    lines_per_page: int = int(os.getenv("BOOK_LINES_PER_PAGE", "40"))
    chars_per_line: int = int(os.getenv("BOOK_CHARS_PER_LINE", "80"))
    alphabet: str = os.getenv("ALPHABET", "abcdefghijklmnopqrstuvwxyz ,.")
    
    # Performance settings
    max_book_size_mb: int = int(os.getenv("MAX_BOOK_SIZE_MB", "10"))
    lazy_loading: bool = os.getenv("LAZY_LOADING", "true").lower() == "true"
    
    @property
    def total_chars(self) -> int:
        """Calculate total characters per book."""
        return self.pages * self.lines_per_page * self.chars_per_line
    
    @property
    def alphabet_size(self) -> int:
        """Get the size of the alphabet."""
        return len(self.alphabet)
    
    @property
    def total_possible_books(self) -> int:
        """Calculate total possible books (theoretical)."""
        return self.alphabet_size ** self.total_chars
    
    def validate(self) -> None:
        """Validate the book configuration."""
        if self.pages <= 0:
            raise ValueError("Pages must be positive")
        if self.lines_per_page <= 0:
            raise ValueError("Lines per page must be positive")
        if self.chars_per_line <= 0:
            raise ValueError("Characters per line must be positive")
        if len(self.alphabet) < 2:
            raise ValueError("Alphabet must contain at least 2 characters")
        if self.max_book_size_mb <= 0:
            raise ValueError("Max book size must be positive")


@dataclass
class CacheConfig:
    """Configuration for caching."""
    
    enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    ttl: int = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default
    max_size: int = int(os.getenv("CACHE_MAX_SIZE", "10000"))
    backend: str = os.getenv("CACHE_BACKEND", "memory")  # memory, redis, azure
    compression: bool = os.getenv("CACHE_COMPRESSION", "false").lower() == "true"
    
    def validate(self) -> None:
        """Validate the cache configuration."""
        if self.ttl <= 0:
            raise ValueError("Cache TTL must be positive")
        if self.max_size <= 0:
            raise ValueError("Cache max size must be positive")
        if self.backend not in ["memory", "redis", "azure"]:
            raise ValueError(f"Invalid cache backend: {self.backend}")


@dataclass
class SecurityConfig:
    """Security configuration."""
    
    # Rate limiting
    rate_limit: str = os.getenv("RATE_LIMIT", "100/minute")
    rate_limit_search: str = os.getenv("RATE_LIMIT_SEARCH", "20/minute")
    rate_limit_regex: str = os.getenv("RATE_LIMIT_REGEX", "10/minute")
    
    # Authentication
    secret_key: str = os.getenv("SECRET_KEY", "")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    enable_auth: bool = os.getenv("ENABLE_AUTH", "false").lower() == "true"
    
    # CORS
    cors_origins: List[str] = field(default_factory=lambda: 
        os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = field(default_factory=lambda: 
        os.getenv("CORS_METHODS", "GET,POST,OPTIONS").split(",")
    )
    cors_allow_headers: List[str] = field(default_factory=lambda: 
        os.getenv("CORS_HEADERS", "Authorization,Content-Type").split(",")
    )
    
    # Input validation
    max_query_length: int = int(os.getenv("MAX_QUERY_LENGTH", "100"))
    max_regex_length: int = int(os.getenv("MAX_REGEX_LENGTH", "50"))
    max_range_size: int = int(os.getenv("MAX_RANGE_SIZE", "100"))
    
    # Security headers
    enable_security_headers: bool = True
    
    def validate(self) -> None:
        """Validate security configuration."""
        if self.access_token_expire_minutes <= 0:
            raise ValueError("Access token expire minutes must be positive")
        if self.max_query_length <= 0:
            raise ValueError("Max query length must be positive")
        if self.max_regex_length <= 0:
            raise ValueError("Max regex length must be positive")
        if self.max_range_size <= 0:
            raise ValueError("Max range size must be positive")


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    
    prometheus_enabled: bool = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
    prometheus_port: int = int(os.getenv("PROMETHEUS_PORT", "8001"))
    json_logging: bool = os.getenv("JSON_LOGGING", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    def validate(self) -> None:
        """Validate monitoring configuration."""
        if self.prometheus_port < 1 or self.prometheus_port > 65535:
            raise ValueError("Prometheus port must be between 1 and 65535")
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.log_level}")


@dataclass
class AppConfig:
    """Main application configuration."""
    
    name: str = os.getenv("APP_NAME", "Library of Babel")
    version: str = os.getenv("APP_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    port: int = int(os.getenv("PORT", "8000"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Sub-configurations
    azure: AzureConfig = field(default_factory=AzureConfig)
    book: BookConfig = field(default_factory=BookConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    def validate(self) -> None:
        """Validate the entire configuration."""
        self.book.validate()
        self.cache.validate()
        self.security.validate()
        self.monitoring.validate()
        
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
