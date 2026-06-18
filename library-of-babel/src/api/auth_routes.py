"""
Authentication API routes for the Library of Babel.

This module provides the API endpoints for authentication and token management.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any

from ..config import get_config
from ..auth.dependencies import (
    login_for_access_token,
    refresh_token,
    get_current_user,
    get_optional_current_user,
    get_admin_user,
)
from ..auth.service import auth_service
from ..monitoring import monitor_api_request

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/token", response_model=Dict[str, str], summary="Get access token")
async def get_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    """
    Get an access token using username and password.
    
    This endpoint implements the OAuth2 password flow for obtaining
    an access token.
    
    Args:
        form_data: OAuth2 password request form with username and password
    
    Returns:
        Access token and token type
    
    Raises:
        HTTPException: If authentication fails
    """
    return await login_for_access_token(form_data)


@router.post("/refresh", response_model=Dict[str, str], summary="Refresh access token")
async def post_refresh_token(
    request: Request,
    refresh_token: str
) -> Dict[str, str]:
    """
    Refresh an access token using a refresh token.
    
    Args:
        refresh_token: The refresh token to use
    
    Returns:
        New access token and token type
    
    Raises:
        HTTPException: If the refresh token is invalid
    """
    return await refresh_token(refresh_token)


@router.get("/me", response_model=Dict[str, Any], summary="Get current user")
async def get_me(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get information about the current authenticated user.
    
    Args:
        current_user: The current user from JWT token
    
    Returns:
        User information
    """
    return {
        "username": current_user.get("username"),
        "is_authenticated": current_user.get("is_authenticated", False),
        "is_admin": current_user.get("is_admin", False),
    }


@router.get("/status", response_model=Dict[str, Any], summary="Authentication status")
async def get_auth_status(
    current_user: Dict[str, Any] = Depends(get_optional_current_user)
) -> Dict[str, Any]:
    """
    Get the current authentication status.
    
    This endpoint returns the authentication status without requiring
    authentication.
    
    Args:
        current_user: The current user (optional)
    
    Returns:
        Authentication status
    """
    config = get_config()
    return {
        "auth_enabled": config.security.enable_auth,
        "is_authenticated": current_user.get("is_authenticated", False),
        "username": current_user.get("username"),
    }


@router.post("/hash-password", response_model=Dict[str, str], summary="Hash a password")
async def hash_password(
    password: str,
    current_user: Dict[str, Any] = Depends(get_admin_user)
) -> Dict[str, str]:
    """
    Hash a password using the application's password hashing algorithm.
    
    This endpoint is for administrative use only.
    
    Args:
        password: The password to hash
        current_user: Admin user
    
    Returns:
        The hashed password
    
    Raises:
        HTTPException: If user is not authorized
    """
    hashed_password = auth_service.get_password_hash(password)
    return {"hashed_password": hashed_password}


@router.post("/verify-password", response_model=Dict[str, bool], summary="Verify a password")
async def verify_password(
    password: str,
    hashed_password: str,
    current_user: Dict[str, Any] = Depends(get_admin_user)
) -> Dict[str, bool]:
    """
    Verify a password against its hash.
    
    This endpoint is for administrative use only.
    
    Args:
        password: The password to verify
        hashed_password: The hashed password to verify against
        current_user: Admin user
    
    Returns:
        Whether the password matches the hash
    
    Raises:
        HTTPException: If user is not authorized
    """
    is_valid = auth_service.verify_password(password, hashed_password)
    return {"is_valid": is_valid}
