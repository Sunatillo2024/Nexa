# import pytest
# from fastapi.testclient import TestClient
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from app.main import app
# from app.database import Base, get_db
# from app import models
#
# # Test database
# SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
# engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#
# # Create tables
# Base.metadata.create_all(bind=engine)
#
#
# def override_get_db():
#     try:
#         db = TestingSessionLocal()
#         yield db
#     finally:
#         db.close()
#
#
# app.dependency_overrides[get_db] = override_get_db
# client = TestClient(app)
#
#
# @pytest.fixture
# def test_user():
#     """Create a test user and return credentials"""
#     user_data = {
#         "username": "testuser",
#         "email": "test@example.com",
#         "password": "testpass123"
#     }
#     response = client.post("/api/auth/register", json=user_data)
#     assert response.status_code == 201
#     return user_data
#
#
# @pytest.fixture
# def auth_token(test_user):
#     """Get authentication token"""
#     response = client.post("/api/auth/login", json={
#         "username": test_user["username"],
#         "password": test_user["password"]
#     })
#     assert response.status_code == 200
#     return response.json()["access_token"]
#
#
# def test_health_check():
#     """Test health check endpoint"""
#     response = client.get("/health")
#     assert response.status_code == 200
#     data = response.json()
#     assert "status" in data
#     assert "database" in data
#
#
# def test_root():
#     """Test root endpoint"""
#     response = client.get("/")
#     assert response.status_code == 200
#     data = response.json()
#     assert "name" in data
#     assert "version" in data
#
#
# def test_register_user():
#     """Test user registration"""
#     response = client.post("/api/auth/register", json={
#         "username": "newuser",
#         "email": "newuser@example.com",
#         "password": "password123"
#     })
#     assert response.status_code == 201
#     data = response.json()
#     assert data["username"] == "newuser"
#     assert "id" in data
#
#
# def test_register_duplicate_username(test_user):
#     """Test registration with duplicate username"""
#     response = client.post("/api/auth/register", json={
#         "username": test_user["username"],
#         "email": "another@example.com",
#         "password": "password123"
#     })
#     assert response.status_code == 400
#
#
# def test_login(test_user):
#     """Test user login"""
#     response = client.post("/api/auth/login", json={
#         "username": test_user["username"],
#         "password": test_user["password"]
#     })
#     assert response.status_code == 200
#     data = response.json()
#     assert "access_token" in data
#     assert data["token_type"] == "bearer"
#
#
# def test_login_wrong_password(test_user):
#     """Test login with wrong password"""
#     response = client.post("/api/auth/login", json={
#         "username": test_user["username"],
#         "password": "wrongpassword"
#     })
#     assert response.status_code == 401
#
#
# def test_get_current_user(auth_token):
#     """Test getting current user info"""
#     response = client.get(
#         "/api/auth/me",
#         headers={"Authorization": f"Bearer {auth_token}"}
#     )
#     assert response.status_code == 200
#     data = response.json()
#     assert "username" in data
#
#
# def test_update_presence(auth_token):
#     """Test updating user presence"""
#     response = client.post(
#         "/api/presence/update?status=online",
#         headers={"Authorization": f"Bearer {auth_token}"}
#     )
#     assert response.status_code == 200
#     data = response.json()
#     assert data["status"] == "success"
#
#
# def test_start_call_unauthorized():
#     """Test starting call without authentication"""
#     response = client.post("/api/calls/start", json={
#         "caller_id": "user1",
#         "receiver_id": "user2"
#     })
#     assert response.status_code == 401
#
#
# def test_get_active_calls(auth_token):
#     """Test getting active calls"""
#     response = client.get(
#         "/api/calls/active",
#         headers={"Authorization": f"Bearer {auth_token}"}
#     )
#     assert response.status_code == 200
#     assert isinstance(response.json(), list)
#
#
# def test_get_call_history(auth_token):
#     """Test getting call history"""
#     response = client.get(
#         "/api/calls/history",
#         headers={"Authorization": f"Bearer {auth_token}"}
#     )
#     assert response.status_code == 200
#     data = response.json()
#     assert "calls" in data
#     assert "total" in data
#
#
# # Cleanup
# def teardown_module(module):
#     """Clean up test database"""
#     Base.metadata.drop_all(bind=engine)
#
#

#
# # from app.database import SessionLocal
# # db = SessionLocal()
# # try:
# #     result = db.execute("SELECT 1")
# #     print("✅ Database connection working")
# #     # Test if users table exists
# #     result = db.execute("SELECT * FROM users LIMIT 1")
# #     print("✅ Users table exists")
# # except Exception as e:
# #     print(f"❌ Database error: {e}")
# # finally:
# #     db.close()