from builtins import str
import pytest
from httpx import AsyncClient
from app.main import app
from app.models.user_model import User, UserRole
from app.utils.nickname_gen import generate_nickname
from app.utils.security import hash_password
from app.services.jwt_service import decode_token  # Import your FastAPI app
from datetime import datetime, timedelta
from tests.conftest import db_session
from sqlalchemy.future import select 
from unittest.mock import patch 



# Example of a test function using the async_client fixture
@pytest.mark.asyncio
async def test_create_user_access_denied(async_client, user_token, email_service):
    headers = {"Authorization": f"Bearer {user_token}"}
    # Define user data for the test
    user_data = {
        "nickname": generate_nickname(),
        "email": "test@example.com",
        "password": "sS#fdasrongPassword123!",
    }
    # Send a POST request to create a user
    response = await async_client.post("/users/", json=user_data, headers=headers)
    # Asserts
    assert response.status_code == 403

# You can similarly refactor other test functions to use the async_client fixture
@pytest.mark.asyncio
async def test_retrieve_user_access_denied(async_client, verified_user, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await async_client.get(f"/users/{verified_user.id}", headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_retrieve_user_access_allowed(async_client, admin_user, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.get(f"/users/{admin_user.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(admin_user.id)

@pytest.mark.asyncio
async def test_update_user_email_access_denied(async_client, verified_user, user_token):
    updated_data = {"email": f"updated_{verified_user.id}@example.com"}
    headers = {"Authorization": f"Bearer {user_token}"}
    response = await async_client.put(f"/users/{verified_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_update_user_email_access_allowed(async_client, admin_user, admin_token):
    updated_data = {"email": f"updated_{admin_user.id}@example.com"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == updated_data["email"]


@pytest.mark.asyncio
async def test_delete_user(async_client, admin_user, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    delete_response = await async_client.delete(f"/users/{admin_user.id}", headers=headers)
    assert delete_response.status_code == 204
    # Verify the user is deleted
    fetch_response = await async_client.get(f"/users/{admin_user.id}", headers=headers)
    assert fetch_response.status_code == 404

@pytest.mark.asyncio
async def test_create_user_duplicate_email(async_client, verified_user):
    user_data = {
        "email": verified_user.email,
        "password": "AnotherPassword123!",
        "role": UserRole.ADMIN.name
    }
    response = await async_client.post("/register/", json=user_data)
    assert response.status_code == 400
    assert "Email already exists" in response.json().get("detail", "")

@pytest.mark.asyncio
async def test_create_user_invalid_email(async_client):
    user_data = {
        "email": "notanemail",
        "password": "ValidPassword123!",
    }
    response = await async_client.post("/register/", json=user_data)
    assert response.status_code == 422

import pytest
from app.services.jwt_service import decode_token
from urllib.parse import urlencode

@pytest.mark.asyncio
async def test_login_success(async_client, verified_user):
    # Attempt to login with the test user
    form_data = {
        "username": verified_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    
    # Check for successful login response
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Use the decode_token method from jwt_service to decode the JWT
    decoded_token = decode_token(data["access_token"])
    assert decoded_token is not None, "Failed to decode token"
    assert decoded_token["role"] == "AUTHENTICATED", "The user role should be AUTHENTICATED"

@pytest.mark.asyncio
async def test_login_user_not_found(async_client):
    form_data = {
        "username": "nonexistentuser@here.edu",
        "password": "DoesNotMatter123!"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 401
    assert "Incorrect email or password." in response.json().get("detail", "")

@pytest.mark.asyncio
async def test_login_incorrect_password(async_client, verified_user):
    form_data = {
        "username": verified_user.email,
        "password": "IncorrectPassword123!"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 401
    assert "Incorrect email or password." in response.json().get("detail", "")

@pytest.mark.asyncio
async def test_login_unverified_user(async_client, unverified_user):
    form_data = {
        "username": unverified_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_login_locked_user(async_client, locked_user):
    form_data = {
        "username": locked_user.email,
        "password": "MySuperPassword$1234"
    }
    response = await async_client.post("/login/", data=urlencode(form_data), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 400
    assert "Account locked due to too many failed login attempts." in response.json().get("detail", "")
@pytest.mark.asyncio
async def test_delete_user_does_not_exist(async_client, admin_token):
    non_existent_user_id = "00000000-0000-0000-0000-000000000000"  # Valid UUID format
    headers = {"Authorization": f"Bearer {admin_token}"}
    delete_response = await async_client.delete(f"/users/{non_existent_user_id}", headers=headers)
    assert delete_response.status_code == 404

@pytest.mark.asyncio
async def test_update_user_github(async_client, admin_user, admin_token):
    updated_data = {"github_profile_url": "http://www.github.com/kaw393939"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["github_profile_url"] == updated_data["github_profile_url"]

@pytest.mark.asyncio
async def test_update_user_linkedin(async_client, admin_user, admin_token):
    updated_data = {"linkedin_profile_url": "http://www.linkedin.com/kaw393939"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["linkedin_profile_url"] == updated_data["linkedin_profile_url"]

@pytest.mark.asyncio
async def test_list_users_as_admin(async_client, admin_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert 'items' in response.json()

@pytest.mark.asyncio
async def test_list_users_as_manager(async_client, manager_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_list_users_unauthorized(async_client, user_token):
    response = await async_client.get(
        "/users/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403  # Forbidden, as expected for regular user

#NEW TEST CASES
@pytest.mark.asyncio 
async def test_search_user_nickname(async_client, admin_token):
    nickname = generate_nickname()
    mock_email = 'testemailnickname@example.com'

    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': UserRole.ADMIN.name 
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email

        search_response = await async_client.post(
            "/users/search", 
            params={"nickname": nickname},   
            headers=headers
        )
        assert search_response.status_code == 200   
        users_data = search_response.json()
        
        assert any(user['nickname'] == nickname for user in users_data['items'])


@pytest.mark.asyncio 
async def test_search_user_email(async_client, admin_token):
    nickname = generate_nickname()
    mock_email = 'testemailemail@example.com'

    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': UserRole.ADMIN.name 
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email

        search_response = await async_client.post(
            "/users/search", 
            params={"email": mock_email},   
            headers=headers
        )
        assert search_response.status_code == 200   
        users_data = search_response.json()
        
        assert any(user['email'] == mock_email for user in users_data['items'])


@pytest.mark.asyncio 
async def test_search_user_role(async_client, admin_token):
    nickname = generate_nickname()
    mock_email = 'testemailrole@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name


        search_response = await async_client.post(
            "/users/search", 
            params={"role": mock_role.name},   
            headers=headers
        )
        assert search_response.status_code == 200   
        users_data = search_response.json()
        
        assert users_data['total'] > 0 
        assert any(user['role'] == mock_role.name for user in users_data['items'])


@pytest.mark.asyncio 
async def test_search_user_email_and_nickname(async_client, admin_token):
    nickname = generate_nickname()
    mock_email = 'testemailemailandnickname@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name


        search_response = await async_client.post(
            "/users/search", 
            params={"email": mock_email, "nickname": nickname},   
            headers=headers
        )
        assert search_response.status_code == 200   
        users_data = search_response.json()
        
        assert any(user['email'] == mock_email and user['nickname'] == nickname for user in users_data['items'])


@pytest.mark.asyncio 
async def test_search_user_email_and_role(async_client, admin_token):
    nickname = generate_nickname()
    mock_email = 'testemailemailandrole@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name

        #mental note - first searching by users (since the email has to be unique to one user)
        search_response = await async_client.post(
            "/users/search", 
            params={"email": mock_email},   
            headers=headers
        )
        assert search_response.status_code == 200   
        users_data = search_response.json()
        

        filtered_users = [
            user for user in users_data['items'] if user['role'] == mock_role.name
        ]

        #making sure that the role matches with the user, so that both conditions are met
        user_found = False
        for user in filtered_users:
            if user['email'] == mock_email and user['role'] == mock_role.name:
                user_found = True 
                break 
        
        assert user_found 

from unittest.mock import patch 
@pytest.mark.asyncio 
async def test_search_user_nickname_and_role(async_client, admin_token):
    nickname = generate_nickname()
    mock_email = 'testemailnicknameandrole@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }

    headers = {"Authorization": f"Bearer {admin_token}"}
    #using mock tests to prevent too many emails from being sent in the test cases to the apis endpoints bc this will cause errors
    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
            
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name

        search_response = await async_client.post(
            "/users/search", 
            params={"nickname": nickname},   
            headers=headers
        )
        assert search_response.status_code == 200   
        users_data = search_response.json()
        

        filtered_users = [
            user for user in users_data['items'] if user['role'] == mock_role.name
        ]

        user_found = False
        for user in filtered_users:
            if user['nickname'] == nickname and user['role'] == mock_role.name:
                user_found = True 
                break 
        
        assert user_found 

#test case for other api endpoint 
@pytest.mark.asyncio
async def test_filter_by_date_range(async_client, admin_token, db_session):
    nickname = generate_nickname()
    mock_email = 'testemailsuccessfuldaterange@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }
    
    #note - creating new user in the database
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name

    #filtering to get the date the user was created 
    stmt = select(User).filter_by(email=mock_email) 
    result = await db_session.execute(stmt) 
    user_in_db = result.scalars().first()

    #retrieves the date of creation from the database
    user_creation_date = user_in_db.created_at.date()

    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=365)

    assert start_date <= user_creation_date <= end_date

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')


    response = await async_client.post(
        '/users/date',
        params = {'start_date': start_date_str, 'end_date': end_date_str},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 200

    response_data = response.json()
    user_found = any(user['email'] == created_user['email'] for user in response_data['items'])

    assert user_found

@pytest.mark.asyncio
async def test_filter_by_incorrect_start_date(async_client, admin_token, db_session):
    nickname = generate_nickname()
    mock_email = 'testemailincorrectstartdate@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name

    stmt = select(User).filter_by(email=mock_email) 
    result = await db_session.execute(stmt) 
    user_in_db = result.scalars().first()

    user_creation_date = user_in_db.created_at.date()

    end_date = datetime.today().date()
    start_date_wrong = "2025-14-32"

    assert start_date_wrong != user_creation_date
    end_date_str = end_date.strftime('%Y-%m-%d')


    response = await async_client.post(
        '/users/date',
        params = {'start_date': start_date_wrong, 'end_date': end_date_str},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_filter_by_incorrect_end_date(async_client, admin_token, db_session):
    nickname = generate_nickname()
    mock_email = 'testemailincorrectenddate@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name

    stmt = select(User).filter_by(email=mock_email) 
    result = await db_session.execute(stmt) 
    user_in_db = result.scalars().first()

    user_creation_date = user_in_db.created_at.date()

    end_date_wrong = "20215-112-331"
    start_date = datetime.today().date()

    assert end_date_wrong != user_creation_date
    start_date_str = start_date.strftime('%Y-%m-%d')


    response = await async_client.post(
        '/users/date',
        params = {'start_date': start_date, 'end_date': end_date_wrong},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_filter_start_date_after_end_date(async_client, admin_token, db_session):
    nickname = generate_nickname()
    mock_email = 'testemailstartafterend@example.com'
    mock_role = UserRole.ADMIN


    user_data = {
        'nickname': nickname, 
        'email': mock_email,
        'password': 'ValidPassword123',
        'role': mock_role.name 
    }
    
    headers = {"Authorization": f"Bearer {admin_token}"}

    with patch('app.services.email_service.EmailService.send_verification_email') as mock_send_email:
        mock_send_email.return_value = None

        create_response = await async_client.post("/users/", json=user_data, headers=headers)
        assert create_response.status_code == 201
        created_user = create_response.json()
        assert created_user['nickname'] == nickname
        assert created_user['email'] == mock_email
        assert created_user['role'] == mock_role.name

    stmt = select(User).filter_by(email=mock_email) 
    result = await db_session.execute(stmt) 
    user_in_db = result.scalars().first()

    user_creation_date = user_in_db.created_at.date()

    end_date = datetime.today().date()
    start_date_past_end =  (datetime.today().date() + timedelta(days=1)).strftime('%Y-%m-%d')

    assert start_date_past_end > end_date.strftime('%Y-%m-%d')


    response = await async_client.post(
        '/users/date',
        params = {'start_date': start_date_past_end, 'end_date': end_date},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    assert response.status_code == 400
 