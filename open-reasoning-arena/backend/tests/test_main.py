"""Tests for main application endpoints."""

import pytest
from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "docs" in data
    
    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "cache" in data
        assert "version" in data
        assert "environment" in data


class TestUserEndpoints:
    """Test user endpoints."""
    
    def test_create_user(self, client):
        """Test creating a new user."""
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123",
            "is_human": True,
        }
        response = client.post("/users/", json=user_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert data["reputation"] == 0
    
    def test_create_duplicate_user(self, client):
        """Test creating a duplicate user."""
        user_data = {
            "username": "duplicate_user",
            "email": "duplicate@example.com",
            "password": "testpassword123",
            "is_human": True,
        }
        # Create first user
        client.post("/users/", json=user_data)
        
        # Try to create duplicate
        response = client.post("/users/", json=user_data)
        assert response.status_code == status.HTTP_409_CONFLICT
    
    def test_get_user(self, client):
        """Test getting a user by ID."""
        # Create a user first
        user_data = {
            "username": "getuser",
            "email": "get@example.com",
            "password": "testpassword123",
            "is_human": True,
        }
        create_response = client.post("/users/", json=user_data)
        user_id = create_response.json()["id"]
        
        # Get the user
        response = client.get(f"/users/{user_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == user_id
        assert data["username"] == user_data["username"]
    
    def test_get_nonexistent_user(self, client):
        """Test getting a non-existent user."""
        response = client.get("/users/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTaskEndpoints:
    """Test task endpoints."""
    
    def test_create_task(self, client):
        """Test creating a new task."""
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "category": "test",
            "difficulty": 1,
            "is_objective": True,
            "expected_answer": "test answer",
        }
        response = client.post("/tasks/", json=task_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["description"] == task_data["description"]
        assert data["category"] == task_data["category"]
        assert "id" in data
    
    def test_get_tasks(self, client):
        """Test getting all tasks."""
        # Create a task first
        task_data = {
            "title": "List Task",
            "description": "Test task for listing",
            "category": "test",
            "difficulty": 2,
            "is_objective": False,
        }
        client.post("/tasks/", json=task_data)
        
        response = client.get("/tasks/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
    
    def test_get_task(self, client):
        """Test getting a task by ID."""
        # Create a task first
        task_data = {
            "title": "Get Task",
            "description": "Test task for getting",
            "category": "test",
            "difficulty": 3,
            "is_objective": True,
        }
        create_response = client.post("/tasks/", json=task_data)
        task_id = create_response.json()["id"]
        
        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == task_id
    
    def test_get_nonexistent_task(self, client):
        """Test getting a non-existent task."""
        response = client.get("/tasks/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSolutionEndpoints:
    """Test solution endpoints."""
    
    def test_create_solution(self, client):
        """Test creating a new solution."""
        # Create a task first
        task_data = {
            "title": "Solution Task",
            "description": "Task for solution test",
            "category": "test",
            "difficulty": 2,
            "is_objective": True,
            "expected_answer": "correct",
        }
        task_response = client.post("/tasks/", json=task_data)
        task_id = task_response.json()["id"]
        
        # Create solution
        solution_data = {
            "task_id": task_id,
            "model_name": "test-model",
            "answer": "correct",
        }
        response = client.post("/solutions/", json=solution_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["task_id"] == task_id
        assert data["model_name"] == solution_data["model_name"]
        assert "id" in data
    
    def test_get_solutions_for_task(self, client):
        """Test getting solutions for a task."""
        # Create a task
        task_data = {
            "title": "Solutions Task",
            "description": "Task for solutions test",
            "category": "test",
            "difficulty": 1,
            "is_objective": True,
        }
        task_response = client.post("/tasks/", json=task_data)
        task_id = task_response.json()["id"]
        
        # Create a solution
        solution_data = {
            "task_id": task_id,
            "model_name": "test-model",
            "answer": "test answer",
        }
        client.post("/solutions/", json=solution_data)
        
        # Get solutions for task
        response = client.get(f"/tasks/{task_id}/solutions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestChallengeEndpoints:
    """Test challenge endpoints."""
    
    def test_create_challenge(self, client):
        """Test creating a new challenge."""
        # Create a task
        task_data = {
            "title": "Challenge Task",
            "description": "Task for challenge test",
            "category": "test",
            "difficulty": 2,
            "is_objective": True,
        }
        task_response = client.post("/tasks/", json=task_data)
        task_id = task_response.json()["id"]
        
        # Create a solution
        solution_data = {
            "task_id": task_id,
            "model_name": "test-model",
            "answer": "test answer",
        }
        solution_response = client.post("/solutions/", json=solution_data)
        solution_id = solution_response.json()["id"]
        
        # Create challenge
        challenge_data = {
            "solution_id": solution_id,
            "counterexample": "This is a counterexample",
        }
        response = client.post("/challenges/", json=challenge_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["solution_id"] == solution_id
        assert data["counterexample"] == challenge_data["counterexample"]
        assert data["status"] == "pending"
    
    def test_accept_challenge(self, client):
        """Test accepting a challenge."""
        # Create task, solution, and challenge
        task_data = {
            "title": "Accept Challenge Task",
            "description": "Task for accept challenge test",
            "category": "test",
            "difficulty": 1,
            "is_objective": True,
        }
        task_response = client.post("/tasks/", json=task_data)
        task_id = task_response.json()["id"]
        
        solution_data = {
            "task_id": task_id,
            "model_name": "test-model",
            "answer": "test answer",
        }
        solution_response = client.post("/solutions/", json=solution_data)
        solution_id = solution_response.json()["id"]
        
        challenge_data = {
            "solution_id": solution_id,
            "counterexample": "This is a counterexample",
        }
        challenge_response = client.post("/challenges/", json=challenge_data)
        challenge_id = challenge_response.json()["id"]
        
        # Accept challenge
        response = client.post(f"/challenges/{challenge_id}/accept")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Challenge accepted"


class TestLeaderboardEndpoints:
    """Test leaderboard endpoints."""
    
    def test_get_leaderboard(self, client):
        """Test getting the leaderboard."""
        response = client.get("/leaderboard/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "models" in data
        assert isinstance(data["models"], list)


class TestModelFingerprintEndpoints:
    """Test model fingerprint endpoints."""
    
    def test_create_fingerprint(self, client):
        """Test creating a model fingerprint."""
        fingerprint_data = {
            "model_name": "test-model",
            "fingerprint": "a" * 64,  # SHA-256 hash length
        }
        response = client.post("/fingerprints/", json=fingerprint_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["model_name"] == fingerprint_data["model_name"]
        assert data["fingerprint"] == fingerprint_data["fingerprint"]
    
    def test_get_fingerprint(self, client):
        """Test getting a model fingerprint."""
        # Create fingerprint first
        fingerprint_data = {
            "model_name": "get-fingerprint-model",
            "fingerprint": "b" * 64,
        }
        client.post("/fingerprints/", json=fingerprint_data)
        
        # Get fingerprint
        response = client.get("/fingerprints/get-fingerprint-model")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["model_name"] == fingerprint_data["model_name"]


class TestScoreEndpoints:
    """Test score endpoints."""
    
    def test_create_score(self, client):
        """Test creating a score."""
        # Create task and solution
        task_data = {
            "title": "Score Task",
            "description": "Task for score test",
            "category": "test",
            "difficulty": 1,
            "is_objective": True,
        }
        task_response = client.post("/tasks/", json=task_data)
        task_id = task_response.json()["id"]
        
        solution_data = {
            "task_id": task_id,
            "model_name": "test-model",
            "answer": "test answer",
        }
        solution_response = client.post("/solutions/", json=solution_data)
        solution_id = solution_response.json()["id"]
        
        # Create score
        score_data = {
            "solution_id": solution_id,
            "score": 85.5,
            "feedback": "Good answer",
            "is_automated": False,
        }
        response = client.post("/scores/", json=score_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["solution_id"] == solution_id
        assert data["score"] == score_data["score"]
    
    def test_get_scores_for_solution(self, client):
        """Test getting scores for a solution."""
        # Create task and solution
        task_data = {
            "title": "Scores Task",
            "description": "Task for scores test",
            "category": "test",
            "difficulty": 1,
            "is_objective": True,
        }
        task_response = client.post("/tasks/", json=task_data)
        task_id = task_response.json()["id"]
        
        solution_data = {
            "task_id": task_id,
            "model_name": "test-model",
            "answer": "test answer",
        }
        solution_response = client.post("/solutions/", json=solution_data)
        solution_id = solution_response.json()["id"]
        
        # Create score
        score_data = {
            "solution_id": solution_id,
            "score": 90.0,
            "feedback": "Excellent",
        }
        client.post("/scores/", json=score_data)
        
        # Get scores for solution
        response = client.get(f"/solutions/{solution_id}/scores")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
