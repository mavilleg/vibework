"""
Authentication and Authorization Module for Open Reasoning Arena.

This module provides JWT-based authentication, user management, and authorization
utilities for the Open Reasoning Arena backend.

Features:
- JWT token generation and validation
- Password hashing with bcrypt
- User model and database operations
- Role-based access control (RBAC)
- Token blacklisting for logout
- Refresh token support

Author: Vibe Code Agent
Created: 2026-06-18
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, List, Optional, Tuple

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from .config import get_config
from .database import get_db
from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    NotFoundError,
)
from .monitoring import (
    AUTH_TOKEN_CREATED,
    AUTH_TOKEN_INVALIDATED,
    AUTH_TOKEN_REFRESHED,
    AUTH_TOKEN_VALIDATED,
    increment_auth_failure,
)

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for token authentication
security = HTTPBearer()


class TokenType(str):
    """Token types for JWT."""
    ACCESS = "access"
    REFRESH = "refresh"


class UserRole(str):
    """User roles for RBAC."""
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class UserBase(BaseModel):
    """Base user model."""
    username: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_]+$')
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=8, max_length=100)


class UserInDB(UserBase):
    """User model with database fields."""
    id: int
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    roles: List[UserRole] = [UserRole.USER]
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserBase):
    """User model for API responses."""
    id: int
    is_active: bool
    roles: List[UserRole]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None


class TokenData(BaseModel):
    """Token data extracted from JWT."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    roles: List[UserRole] = []
    token_type: Optional[TokenType] = None


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str


# Token blacklist for logout (in-memory, should be Redis in production)
_token_blacklist: Dict[str, datetime] = {}

# Refresh token storage (in-memory, should be Redis in production)
_refresh_token_store: Dict[str, TokenData] = {}


def get_auth_config():
    """Get authentication configuration."""
    config = get_config()
    auth_config = config.security
    
    if not auth_config.jwt_secret_key:
        raise ConfigurationError("JWT secret key not configured")
    
    return auth_config


def get_jwt_secret_key() -> str:
    """Get JWT secret key from configuration."""
    return get_auth_config().jwt_secret_key


def get_jwt_algorithm() -> str:
    """Get JWT algorithm from configuration."""
    return get_auth_config().jwt_algorithm


def get_access_token_expire_minutes() -> int:
    """Get access token expiration time in minutes."""
    return get_auth_config().access_token_expire_minutes


def get_refresh_token_expire_days() -> int:
    """Get refresh token expiration time in days."""
    return get_auth_config().refresh_token_expire_days


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: The plain text password to hash.
        
    Returns:
        The hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: The plain text password to verify.
        hashed_password: The hashed password to verify against.
        
    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_token_data(user: UserInDB, token_type: TokenType) -> Dict[str, Any]:
    """
    Generate token data for JWT encoding.
    
    Args:
        user: The user to generate token data for.
        token_type: The type of token (access or refresh).
        
    Returns:
        Dictionary containing token data.
    """
    expire_minutes = (
        get_access_token_expire_minutes() 
        if token_type == TokenType.ACCESS 
        else get_refresh_token_expire_days() * 24 * 60
    )
    
    expires_at = datetime.utcnow() + timedelta(minutes=expire_minutes)
    
    # Generate a unique token ID (jti) for blacklisting
    jti = secrets.token_hex(16)
    
    return {
        "sub": user.username,
        "user_id": user.id,
        "roles": user.roles,
        "token_type": token_type,
        "jti": jti,
        "iat": datetime.utcnow(),
        "exp": expires_at,
        "nbf": datetime.utcnow(),
    }


def create_access_token(user: UserInDB) -> Tuple[str, int]:
    """
    Create a JWT access token for a user.
    
    Args:
        user: The user to create a token for.
        
    Returns:
        Tuple of (token, expires_in_seconds).
    """
    token_data = generate_token_data(user, TokenType.ACCESS)
    
    secret_key = get_jwt_secret_key()
    algorithm = get_jwt_algorithm()
    
    token = jwt.encode(token_data, secret_key, algorithm=algorithm)
    
    expires_in = get_access_token_expire_minutes() * 60
    
    # Track token creation
    increment_auth_failure("token_created", "access")
    AUTH_TOKEN_CREATED.labels(token_type="access").inc()
    
    logger.info(f"Access token created for user {user.username}")
    
    return token, expires_in


def create_refresh_token(user: UserInDB) -> Tuple[str, int]:
    """
    Create a JWT refresh token for a user.
    
    Args:
        user: The user to create a refresh token for.
        
    Returns:
        Tuple of (token, expires_in_seconds).
    """
    token_data = generate_token_data(user, TokenType.REFRESH)
    
    secret_key = get_jwt_secret_key()
    algorithm = get_jwt_algorithm()
    
    token = jwt.encode(token_data, secret_key, algorithm=algorithm)
    
    expires_in = get_refresh_token_expire_days() * 24 * 60 * 60
    
    # Store refresh token
    _refresh_token_store[token] = TokenData(
        username=user.username,
        user_id=user.id,
        roles=user.roles,
        token_type=TokenType.REFRESH,
    )
    
    # Track token creation
    increment_auth_failure("token_created", "refresh")
    AUTH_TOKEN_CREATED.labels(token_type="refresh").inc()
    
    logger.info(f"Refresh token created for user {user.username}")
    
    return token, expires_in


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode.
        
    Returns:
        TokenData extracted from the token.
        
    Raises:
        AuthenticationError: If the token is invalid or expired.
    """
    secret_key = get_jwt_secret_key()
    algorithm = get_jwt_algorithm()
    
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        
        # Check if token is blacklisted
        jti = payload.get("jti")
        if jti and jti in _token_blacklist:
            increment_auth_failure("token_blacklisted", "access")
            raise AuthenticationError("Token has been revoked")
        
        # Check token type
        token_type = payload.get("token_type")
        if not token_type:
            increment_auth_failure("invalid_token_type", "access")
            raise AuthenticationError("Invalid token type")
        
        # Extract user data
        username = payload.get("sub")
        user_id = payload.get("user_id")
        roles = payload.get("roles", [])
        
        token_data = TokenData(
            username=username,
            user_id=user_id,
            roles=roles,
            token_type=token_type,
        )
        
        # Track successful validation
        AUTH_TOKEN_VALIDATED.labels(token_type=token_type).inc()
        
        return token_data
        
    except jwt.ExpiredSignatureError:
        increment_auth_failure("token_expired", "access")
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError as e:
        increment_auth_failure("token_invalid", "access")
        raise AuthenticationError(f"Invalid token: {str(e)}")


def blacklist_token(jti: str) -> None:
    """
    Add a token to the blacklist (logout).
    
    Args:
        jti: The JWT ID to blacklist.
    """
    _token_blacklist[jti] = datetime.utcnow()
    AUTH_TOKEN_INVALIDATED.labels(reason="logout").inc()
    logger.info(f"Token {jti[:8]}... blacklisted")


def invalidate_refresh_token(token: str) -> None:
    """
    Invalidate a refresh token.
    
    Args:
        token: The refresh token to invalidate.
    """
    if token in _refresh_token_store:
        del _refresh_token_store[token]
    AUTH_TOKEN_INVALIDATED.labels(reason="refresh_invalidated").inc()
    logger.info("Refresh token invalidated")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> UserInDB:
    """
    Get the current authenticated user from the JWT token.
    
    Args:
        credentials: HTTP Bearer credentials.
        db: Database session.
        
    Returns:
        The authenticated user.
        
    Raises:
        AuthenticationError: If authentication fails.
    """
    try:
        token = credentials.credentials
        token_data = decode_token(token)
        
        if token_data.token_type != TokenType.ACCESS:
            increment_auth_failure("wrong_token_type", "access")
            raise AuthenticationError("Invalid token type for access")
        
        # Get user from database
        user = get_user_by_username(db, token_data.username)
        
        if not user:
            increment_auth_failure("user_not_found", "access")
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            increment_auth_failure("user_inactive", "access")
            raise AuthenticationError("User is inactive")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        logger.info(f"User {user.username} authenticated successfully")
        
        return user
        
    except AuthenticationError:
        raise
    except Exception as e:
        increment_auth_failure("auth_error", "access")
        logger.error(f"Authentication error: {str(e)}")
        raise AuthenticationError(f"Authentication failed: {str(e)}")


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """
    Get the current active user (alias for get_current_user).
    
    Args:
        current_user: The current user from dependency injection.
        
    Returns:
        The current active user.
        
    Raises:
        AuthenticationError: If the user is not active.
    """
    if not current_user.is_active:
        raise AuthenticationError("Inactive user")
    return current_user


def has_role(user: UserInDB, required_roles: List[UserRole]) -> bool:
    """
    Check if a user has any of the required roles.
    
    Args:
        user: The user to check.
        required_roles: List of required roles.
        
    Returns:
        True if the user has at least one required role.
    """
    user_roles = set(user.roles)
    required_roles_set = set(required_roles)
    return bool(user_roles & required_roles_set)


def has_all_roles(user: UserInDB, required_roles: List[UserRole]) -> bool:
    """
    Check if a user has all of the required roles.
    
    Args:
        user: The user to check.
        required_roles: List of required roles.
        
    Returns:
        True if the user has all required roles.
    """
    user_roles = set(user.roles)
    required_roles_set = set(required_roles)
    return required_roles_set.issubset(user_roles)


async def get_user_with_roles(
    current_user: UserInDB = Depends(get_current_user),
    required_roles: Optional[List[UserRole]] = None,
) -> UserInDB:
    """
    Get the current user and verify they have the required roles.
    
    Args:
        current_user: The current user from dependency injection.
        required_roles: Optional list of required roles.
        
    Returns:
        The current user if authorized.
        
    Raises:
        AuthorizationError: If the user doesn't have the required roles.
    """
    if required_roles and not has_role(current_user, required_roles):
        raise AuthorizationError(
            f"Requires one of: {', '.join(required_roles)}"
        )
    return current_user


async def get_user_with_all_roles(
    current_user: UserInDB = Depends(get_current_user),
    required_roles: Optional[List[UserRole]] = None,
) -> UserInDB:
    """
    Get the current user and verify they have all required roles.
    
    Args:
        current_user: The current user from dependency injection.
        required_roles: Optional list of required roles.
        
    Returns:
        The current user if authorized.
        
    Raises:
        AuthorizationError: If the user doesn't have all required roles.
    """
    if required_roles and not has_all_roles(current_user, required_roles):
        raise AuthorizationError(
            f"Requires all of: {', '.join(required_roles)}"
        )
    return current_user


# User database operations

def get_user_by_username(db: Session, username: str) -> Optional[UserInDB]:
    """
    Get a user by username.
    
    Args:
        db: Database session.
        username: The username to search for.
        
    Returns:
        The user if found, None otherwise.
    """
    from .models import User as UserModel
    
    user = db.query(UserModel).filter(UserModel.username == username).first()
    
    if user:
        return UserInDB.model_validate(user)
    return None


def get_user_by_email(db: Session, email: str) -> Optional[UserInDB]:
    """
    Get a user by email.
    
    Args:
        db: Database session.
        email: The email to search for.
        
    Returns:
        The user if found, None otherwise.
    """
    from .models import User as UserModel
    
    user = db.query(UserModel).filter(UserModel.email == email).first()
    
    if user:
        return UserInDB.model_validate(user)
    return None


def get_user_by_id(db: Session, user_id: int) -> Optional[UserInDB]:
    """
    Get a user by ID.
    
    Args:
        db: Database session.
        user_id: The user ID to search for.
        
    Returns:
        The user if found, None otherwise.
    """
    from .models import User as UserModel
    
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    
    if user:
        return UserInDB.model_validate(user)
    return None


def create_user(db: Session, user_data: UserCreate) -> UserInDB:
    """
    Create a new user.
    
    Args:
        db: Database session.
        user_data: The user data to create.
        
    Returns:
        The created user.
        
    Raises:
        AuthenticationError: If the username or email already exists.
    """
    from .models import User as UserModel
    
    # Check if username exists
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise AuthenticationError("Username already exists")
    
    # Check if email exists
    existing_email = get_user_by_email(db, user_data.email)
    if existing_email:
        raise AuthenticationError("Email already exists")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    now = datetime.utcnow()
    user = UserModel(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
        roles=[UserRole.USER],
        created_at=now,
        updated_at=now,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"User {user_data.username} created successfully")
    
    return UserInDB.model_validate(user)


def authenticate_user(db: Session, username: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate a user with username and password.
    
    Args:
        db: Database session.
        username: The username to authenticate.
        password: The password to verify.
        
    Returns:
        The authenticated user if successful, None otherwise.
    """
    user = get_user_by_username(db, username)
    
    if not user:
        increment_auth_failure("user_not_found", "login")
        return None
    
    if not verify_password(password, user.hashed_password):
        increment_auth_failure("invalid_password", "login")
        return None
    
    if not user.is_active:
        increment_auth_failure("user_inactive", "login")
        return None
    
    return user


async def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db),
) -> Token:
    """
    Refresh an access token using a refresh token.
    
    Args:
        refresh_token: The refresh token to use.
        db: Database session.
        
    Returns:
        New access token.
        
    Raises:
        AuthenticationError: If the refresh token is invalid.
    """
    # Check if refresh token exists
    if refresh_token not in _refresh_token_store:
        increment_auth_failure("invalid_refresh_token", "refresh")
        raise AuthenticationError("Invalid refresh token")
    
    # Get token data from store
    token_data = _refresh_token_store[refresh_token]
    
    # Get user from database
    user = get_user_by_username(db, token_data.username)
    
    if not user or not user.is_active:
        increment_auth_failure("user_not_found_or_inactive", "refresh")
        invalidate_refresh_token(refresh_token)
        raise AuthenticationError("User not found or inactive")
    
    # Create new access token
    access_token, access_expires_in = create_access_token(user)
    
    # Create new refresh token (rotate refresh tokens)
    new_refresh_token, refresh_expires_in = create_refresh_token(user)
    
    # Invalidate old refresh token
    invalidate_refresh_token(refresh_token)
    
    # Track refresh
    AUTH_TOKEN_REFRESHED.inc()
    
    logger.info(f"Token refreshed for user {user.username}")
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=access_expires_in,
        refresh_token=new_refresh_token,
        refresh_expires_in=refresh_expires_in,
    )


async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, str]:
    """
    Logout the current user by blacklisting their token.
    
    Args:
        credentials: HTTP Bearer credentials.
        
    Returns:
        Success message.
    """
    try:
        token = credentials.credentials
        token_data = decode_token(token)
        
        # Blacklist the token
        jti = token_data.jti
        if jti:
            blacklist_token(jti)
        
        logger.info(f"User {token_data.username} logged out")
        
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise AuthenticationError(f"Logout failed: {str(e)}")


# Dependency for optional authentication (for endpoints that work with or without auth)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[UserInDB]:
    """
    Get the current user if authenticated, None otherwise.
    
    Args:
        credentials: Optional HTTP Bearer credentials.
        db: Database session.
        
    Returns:
        The authenticated user or None.
    """
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except AuthenticationError:
        return None
