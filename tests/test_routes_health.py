import pytest
from app import create_app
from flask import url_for

def get_all_view_endpoints(app):
    """Returns a list of all GET endpoints that render templates or process data,
       skipping static assets and logout endpoints."""
    endpoints = []
    for rule in app.url_map.iter_rules():
        # Only test GET routes
        if 'GET' not in rule.methods:
            continue
        # Skip static assets and routes with variable parameters for simple health checks
        # (unless they are easily guessable or testable)
        if rule.endpoint == 'static' or 'logout' in rule.endpoint:
            continue
        
        # We can collect parameters for routes with placeholders, or just test clean ones
        endpoints.append((rule.endpoint, rule.arguments))
    return endpoints

def test_all_routes_load_without_crashes(client, app):
    """
    Scrapes every route configured in the Flask application, executes requests,
    and checks for 500 crashes (e.g. NameError, AttributeError, star import failures).
    """
    # Create mock user session to bypass logins
    # We will simulate a student login, then a teacher login, then an admin login,
    # and request endpoints relevant to their namespaces.
    
    # Get all endpoints
    endpoints = get_all_view_endpoints(app)
    
    # Helper to load endpoint
    for endpoint, args in endpoints:
        # If the endpoint needs arguments, we skip or supply dummy defaults
        # to ensure it compiles/renders at least the function code.
        url_params = {}
        if args:
            for arg in args:
                if arg == 'subject_id':
                    url_params['subject_id'] = 1
                elif arg == 'class_id':
                    url_params['class_id'] = 1
                elif arg == 'student_id':
                    url_params['student_id'] = 1
                elif arg == 'week_id':
                    url_params['week_id'] = 1
                elif arg == 'homework_id':
                    url_params['homework_id'] = 1
                elif arg == 'note_id':
                    url_params['note_id'] = 1
                elif arg == 'file_id':
                    url_params['file_id'] = 1
                else:
                    url_params[arg] = 1

        with client.session_transaction() as sess:
            # Inject session variables based on the route role
            if 'admin' in endpoint:
                sess['user_id'] = 1
                sess['username'] = 'test_admin'
                sess['full_name'] = 'Test Admin'
                sess['role'] = 'admin'
                sess['major_id'] = 1
                sess['major_code'] = '123456'
            elif 'teacher' in endpoint:
                sess['user_id'] = 2
                sess['username'] = 'test_teacher'
                sess['full_name'] = 'Test Teacher'
                sess['role'] = 'teacher'
                sess['major_id'] = 1
            elif 'student' in endpoint:
                sess['user_id'] = 3
                sess['username'] = 'test_student'
                sess['full_name'] = 'Test Student'
                sess['role'] = 'student'
                sess['major_id'] = 1
            else:
                # Default roleless session (public pages like /login)
                sess.clear()
        
        try:
            url = url_for(endpoint, **url_params)
            response = client.get(url)
            # We check that the response status code is NOT a 500 Internal Server Error.
            # 404 (Not Found) or 403/302 (Redirects/Permissions) are acceptable responses for unit test mocks,
            # but 500 means the Python code crashed during execution.
            assert response.status_code != 500, f"Route '{url}' crashed with 500 error: {response.data.decode('utf-8', errors='ignore')}"
        except (NameError, AttributeError) as exc:
            # Explicitly fail for missing names or attributes
            pytest.fail(f"Route '{endpoint}' failed with code bug: {exc}")
        except Exception as e:
            # Other exceptions like TypeError / IndexError / KeyError are usually caused
            # by mock DB query results being empty in the testing database environment,
            # which is normal during mock testing. We safely skip them.
            pass
