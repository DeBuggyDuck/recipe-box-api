from app import create_app
from app.db import init_db

app = create_app("testing")
init_db(app)

client = app.test_client()

register_payload = {
    "username": "test_isolation_user",
    "email": "test_isolation@example.com",
    "password": "IsolationPassword123!",
}
reg_resp = client.post("/register", json=register_payload)
print("REGISTER status:", reg_resp.status_code)
print("REGISTER json:", reg_resp.get_json())

login_payload = {
    "username": "test_isolation_user",
    "password": "IsolationPassword123!",
}
login_resp = client.post("/login", json=login_payload)
print("LOGIN status:", login_resp.status_code)
print("LOGIN json:", login_resp.get_json())