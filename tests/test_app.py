import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_routes_exist(client):
    # Verify that primary routes are registered
    # Let's test reaching the login page, which should always be accessible
    response = client.get('/login')
    assert response.status_code == 200

def test_student_dashboard_redirects_unauthenticated(client):
    # Student dashboard should redirect to login if unauthenticated
    response = client.get('/student/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')

def test_teacher_dashboard_redirects_unauthenticated(client):
    response = client.get('/teacher/dashboard')
    assert response.status_code == 302
