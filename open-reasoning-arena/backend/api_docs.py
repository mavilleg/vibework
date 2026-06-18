"""
API Documentation configuration for Open Reasoning Arena.

This module provides enhanced OpenAPI/Swagger documentation with:
- Custom tags and descriptions
- Example requests and responses
- Security scheme definitions
- Response schemas
"""

from typing import Dict, Any, List, Optional

# API metadata
API_TITLE = "Open Reasoning Arena (ORA)"
API_DESCRIPTION = """
# Open Reasoning Arena (ORA)

A dynamic, adversarial benchmark for evaluating LLM reasoning capabilities.

## Overview

ORA is a platform where:
- **Humans** create reasoning tasks
- **Models** submit solutions to tasks
- **Reviewers** score solutions
- **Challengers** find counterexamples to break solutions

The platform maintains a leaderboard of model performance across various reasoning categories.

## Authentication

Currently, authentication is optional (disabled by default). When enabled, use JWT tokens
in the `Authorization` header:

```
Authorization: Bearer <token>
```

## Rate Limiting

All endpoints have rate limits to prevent abuse:
- General endpoints: 100 requests/minute
- Task endpoints: 30 requests/minute
- Solution endpoints: 20 requests/minute
- Challenge endpoints: 15 requests/minute

## Categories

Tasks are organized into categories:
- `math`: Mathematical reasoning
- `logic`: Logical puzzles
- `code`: Code generation and understanding
- `language`: Language understanding and generation
- `reasoning`: General reasoning tasks

## Difficulty Levels

Tasks have difficulty levels from 1 (easiest) to 5 (hardest).
"""

API_VERSION = "0.2.0"
API_CONTACT = {
    "name": "Open Reasoning Arena Team",
    "email": "ora@openreasoning.arena",
}

API_LICENSE = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}

# Tags for endpoints
tags_metadata = [
    {
        "name": "Health",
        "description": "Health check and status endpoints",
    },
    {
        "name": "Users",
        "description": "User management and profiles",
    },
    {
        "name": "Tasks",
        "description": "Reasoning tasks for models to solve",
    },
    {
        "name": "Solutions",
        "description": "Model solutions to tasks",
    },
    {
        "name": "Scores",
        "description": "Scoring of solutions by reviewers",
    },
    {
        "name": "Challenges",
        "description": "Adversarial challenges to solutions",
    },
    {
        "name": "Leaderboard",
        "description": "Model performance rankings",
    },
    {
        "name": "Fingerprints",
        "description": "Model verification and fingerprinting",
    },
]

# Security schemes
security_schemes = {
    "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT token authentication",
    }
}

# Example responses
example_responses = {
    "400": {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error": "VALIDATION_ERROR",
                    "message": "Input validation failed",
                    "details": {"field": "title", "value": ""}
                }
            }
        }
    },
    "401": {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "error": "AUTHENTICATION_FAILED",
                    "message": "Authentication failed",
                }
            }
        }
    },
    "403": {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {
                    "error": "AUTHORIZATION_FAILED",
                    "message": "Authorization failed",
                }
            }
        }
    },
    "404": {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "error": "NOT_FOUND",
                    "message": "Task not found: 123",
                    "details": {"resource_type": "Task", "resource_id": "123"}
                }
            }
        }
    },
    "429": {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded. Try again in 60 seconds.",
                    "details": {"retry_after": 60}
                }
            }
        },
        "headers": {
            "Retry-After": {
                "description": "Seconds to wait before retrying",
                "schema": {"type": "integer"}
            }
        }
    },
    "500": {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                }
            }
        }
    },
}

# Common parameters
common_parameters = {
    "request": {
        "name": "request",
        "in": "header",
        "required": False,
        "schema": {"type": "object"},
        "description": "FastAPI Request object",
    },
    "db": {
        "name": "db",
        "in": "header",
        "required": False,
        "schema": {"type": "object"},
        "description": "Database session",
    },
}

# Task examples
task_examples = {
    "math": {
        "title": "Solve the equation",
        "description": "Solve for x: 2x + 3 = 7",
        "category": "math",
        "difficulty": 1,
        "is_objective": True,
        "expected_answer": "2",
    },
    "logic": {
        "title": "Logic puzzle",
        "description": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies?",
        "category": "logic",
        "difficulty": 3,
        "is_objective": True,
        "expected_answer": "Yes",
    },
    "code": {
        "title": "Reverse a list",
        "description": "Write Python code to reverse a list in-place",
        "category": "code",
        "difficulty": 2,
        "is_objective": False,
        "expected_answer": None,
    },
}

# Solution examples
solution_examples = {
    "gpt4": {
        "task_id": 1,
        "model_name": "gpt-4",
        "answer": "The solution is 2",
    },
    "llama": {
        "task_id": 1,
        "model_name": "llama-3-70b",
        "answer": "x equals 2",
    },
}

# Score examples
score_examples = {
    "perfect": {
        "solution_id": 1,
        "score": 100.0,
        "feedback": "Perfect answer!",
        "is_automated": False,
    },
    "partial": {
        "solution_id": 1,
        "score": 75.0,
        "feedback": "Correct approach but minor errors",
        "is_automated": False,
    },
}

# Challenge examples
challenge_examples = {
    "valid": {
        "solution_id": 1,
        "counterexample": "What if x = -2? Then 2*(-2) + 3 = -1, not 7",
    },
}

# User examples
user_examples = {
    "human": {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "secure_password_123",
        "is_human": True,
    },
    "model": {
        "username": "gpt-4-bot",
        "email": "gpt-4@openai.com",
        "password": "model_password",
        "is_human": False,
    },
}


def get_openapi_config() -> Dict[str, Any]:
    """Get OpenAPI configuration."""
    return {
        "title": API_TITLE,
        "description": API_DESCRIPTION,
        "version": API_VERSION,
        "contact": API_CONTACT,
        "license": API_LICENSE,
        "tags": tags_metadata,
        "servers": [
            {"url": "http://localhost:8000", "description": "Development server"},
            {"url": "https://api.openreasoning.arena", "description": "Production server"},
        ],
    }


def get_security_schemes() -> Dict[str, Any]:
    """Get security schemes for OpenAPI."""
    return security_schemes


def get_common_responses() -> Dict[str, Any]:
    """Get common response schemas."""
    return example_responses


__all__ = [
    "API_TITLE",
    "API_DESCRIPTION",
    "API_VERSION",
    "API_CONTACT",
    "API_LICENSE",
    "tags_metadata",
    "security_schemes",
    "example_responses",
    "common_parameters",
    "task_examples",
    "solution_examples",
    "score_examples",
    "challenge_examples",
    "user_examples",
    "get_openapi_config",
    "get_security_schemes",
    "get_common_responses",
]
