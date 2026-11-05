import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
import main
import database
import models

client = TestClient(main.app)

def test_full_auth_flow():
    print("=== STARTING AUTH & SECURITY TESTS ===")
    
    # 1. Verify 'users' table exists
    import sqlite3
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    row = cursor.fetchone()
    assert row is not None, "users table does not exist in SQLite!"
    print("✓ 'users' table verified in SQLite database.")
    
    # Check users table schema
    cursor.execute("PRAGMA table_info(users);")
    columns = {col[1]: col[2] for col in cursor.fetchall()}
    print("  Columns:", columns)
    assert "id" in columns
    assert "username" in columns
    assert "password_hash" in columns
    conn.close()

    # 2. Test accessing protected endpoint without token
    res = client.get("/api/invoices")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("✓ Unauthenticated request to /api/invoices correctly rejected with 401 Unauthorized.")

    res = client.get("/api/analytics")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    print("✓ Unauthenticated request to /api/analytics correctly rejected with 401 Unauthorized.")

    # 3. Test user registration
    test_user = "testuser_" + os.urandom(4).hex()
    test_pass = "SecurePass123!"

    reg_res = client.post("/api/register", json={"username": test_user, "password": test_pass})
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    token = reg_data["access_token"]
    print(f"✓ /api/register succeeded for user '{test_user}'.")

    # Duplicate registration should fail
    dup_res = client.post("/api/register", json={"username": test_user, "password": test_pass})
    assert dup_res.status_code == 400
    print("✓ Duplicate username registration correctly blocked with 400.")

    # 4. Test login endpoint /api/token with JSON
    token_res = client.post("/api/token", json={"username": test_user, "password": test_pass})
    assert token_res.status_code == 200, f"Token failed: {token_res.text}"
    token_data = token_res.json()
    assert "access_token" in token_data
    login_token = token_data["access_token"]
    print("✓ /api/token succeeded with JSON payload.")

    # Test login endpoint /api/token with Form Data
    token_form_res = client.post("/api/token", data={"username": test_user, "password": test_pass})
    assert token_form_res.status_code == 200, f"Token form failed: {token_form_res.text}"
    print("✓ /api/token succeeded with Form Data payload.")

    # Test login with invalid password
    bad_login = client.post("/api/token", json={"username": test_user, "password": "wrongpassword"})
    assert bad_login.status_code == 401
    print("✓ Bad password correctly rejected with 401.")

    # 5. Test protected endpoints WITH Bearer token
    headers = {"Authorization": f"Bearer {login_token}"}

    invoices_res = client.get("/api/invoices", headers=headers)
    assert invoices_res.status_code == 200, f"Invoices failed: {invoices_res.text}"
    print(f"✓ Authenticated GET /api/invoices succeeded (retrieved {len(invoices_res.json())} invoices).")

    analytics_res = client.get("/api/analytics", headers=headers)
    assert analytics_res.status_code == 200, f"Analytics failed: {analytics_res.text}"
    print("✓ Authenticated GET /api/analytics succeeded.")

    me_res = client.get("/api/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == test_user
    print("✓ Authenticated GET /api/me succeeded.")

    # 6. Test with invalid/garbage Bearer token
    fake_headers = {"Authorization": "Bearer fake.jwt.token"}
    fake_res = client.get("/api/invoices", headers=fake_headers)
    assert fake_res.status_code == 401
    print("✓ Bogus JWT token correctly rejected with 401.")

    print("\nALL BACKEND AUTH TESTS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    test_full_auth_flow()

