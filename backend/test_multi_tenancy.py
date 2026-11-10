import sys
import os
import uuid

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
import main
import database
import models
from models import Invoice, User

client = TestClient(main.app)

def test_multi_tenancy():
    print("\n=== STARTING MULTI-TENANCY & DATA ISOLATION TESTS ===")

    # 1. Verify schema: invoices table must have user_id column
    import sqlite3
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(invoices);")
    columns = {col[1]: col[2] for col in cursor.fetchall()}
    assert "user_id" in columns, "invoices table missing user_id column!"
    print("✓ Schema verified: 'invoices' table contains 'user_id' column.")
    conn.close()

    # 2. Register User A
    username_a = f"tenant_a_{uuid.uuid4().hex[:6]}"
    password_a = "Password123!"
    reg_a = client.post("/api/register", json={"username": username_a, "password": password_a})
    assert reg_a.status_code == 200, f"Register A failed: {reg_a.text}"
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    me_a = client.get("/api/me", headers=headers_a).json()
    user_a_id = me_a["id"]
    print(f"✓ Created User A: {username_a} (id={user_a_id})")

    # 3. Register User B
    username_b = f"tenant_b_{uuid.uuid4().hex[:6]}"
    password_b = "Password123!"
    reg_b = client.post("/api/register", json={"username": username_b, "password": password_b})
    assert reg_b.status_code == 200, f"Register B failed: {reg_b.text}"
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    me_b = client.get("/api/me", headers=headers_b).json()
    user_b_id = me_b["id"]
    print(f"✓ Created User B: {username_b} (id={user_b_id})")

    # 4. Verify newly created User B initially sees NO invoices
    res_b_empty = client.get("/api/invoices", headers=headers_b)
    assert res_b_empty.status_code == 200
    assert len(res_b_empty.json()) == 0, f"Expected 0 invoices for new user B, got {len(res_b_empty.json())}"
    print("✓ New User B sees 0 invoices (isolation from existing accounts confirmed).")

    # Verify User B analytics is empty
    analytics_b = client.get("/api/analytics", headers=headers_b).json()
    assert analytics_b["metrics"]["invoicesProcessed"] == 0
    assert analytics_b["metrics"]["totalSpent"] == 0.0
    print("✓ New User B analytics strictly scoped to 0 invoices.")

    # 5. User A saves an invoice
    inv_payload_a = {
        "vendorName": "Acme Cloud Services",
        "invoiceNumber": f"INV-A-{uuid.uuid4().hex[:4]}",
        "date": "2026-11-10",
        "totalAmount": 1500.0,
        "subtotal": 1271.19,
        "taxAmount": 228.81,
        "currency": "INR",
        "lineItems": [
            {"description": "Cloud Hosting", "quantity": 1, "unitPrice": 1271.19, "total": 1271.19}
        ]
    }
    save_res_a = client.post("/api/invoices", json=inv_payload_a, headers=headers_a)
    assert save_res_a.status_code == 200, f"Save A failed: {save_res_a.text}"
    saved_inv_a = save_res_a.json()
    inv_a_id = saved_inv_a["id"]
    raw_inv_a_id = int(inv_a_id.replace("INV-", ""))
    print(f"✓ User A saved invoice {inv_a_id} (numeric id={raw_inv_a_id}).")

    # Verify in DB that user_id is user_a_id
    db_session = database.SessionLocal()
    db_inv = db_session.query(Invoice).filter(Invoice.id == raw_inv_a_id).first()
    assert db_inv is not None
    assert db_inv.user_id == user_a_id, f"Expected user_id={user_a_id}, got {db_inv.user_id}"
    db_session.close()
    print(f"✓ Database record confirmed: invoice.user_id == {user_a_id}.")

    # 6. Verify Scoped Querying (GET /invoices)
    # User A sees 1 invoice
    invoices_a = client.get("/api/invoices", headers=headers_a).json()
    assert any(inv["id"] == inv_a_id for inv in invoices_a), "User A should see their invoice!"
    print(f"✓ User A sees their uploaded invoice in GET /api/invoices.")

    # User B STILL sees 0 invoices
    invoices_b = client.get("/api/invoices", headers=headers_b).json()
    assert not any(inv["id"] == inv_a_id for inv in invoices_b), "User B must NOT see User A's invoice!"
    assert len(invoices_b) == 0, f"User B should see 0 invoices, got {len(invoices_b)}"
    print(f"✓ User B does NOT see User A's invoice in GET /api/invoices.")

    # Also test route without /api prefix
    invoices_b_no_api = client.get("/invoices", headers=headers_b).json()
    assert len(invoices_b_no_api) == 0
    print("✓ Scoped querying verified for both /api/invoices and /invoices.")

    # 7. Secure Individual Endpoints: GET /invoices/{id}
    # User A accesses own invoice
    get_own_res = client.get(f"/api/invoices/{inv_a_id}", headers=headers_a)
    assert get_own_res.status_code == 200
    assert get_own_res.json()["vendorName"] == "Acme Cloud Services"
    print(f"✓ User A successfully accessed own invoice via GET /api/invoices/{inv_a_id}.")

    # User B attempts to access User A's invoice -> Must return 403 or 404
    get_cross_res = client.get(f"/api/invoices/{inv_a_id}", headers=headers_b)
    assert get_cross_res.status_code in (403, 404), f"Expected 403/404, got {get_cross_res.status_code}"
    print(f"✓ User B blocked from accessing User A's invoice (HTTP {get_cross_res.status_code}).")

    # Non-existent invoice returns 404
    non_existent_res = client.get("/api/invoices/INV-99999999", headers=headers_a)
    assert non_existent_res.status_code == 404
    print("✓ Non-existent invoice returns 404 Not Found.")

    # 8. Secure Individual Endpoints: Edit (PUT / PATCH)
    update_payload = {"vendorName": "Hacked Vendor", "totalAmount": 999999.0}
    # User B attempts to update User A's invoice -> Must return 403 or 404
    put_cross_res = client.put(f"/api/invoices/{inv_a_id}", json=update_payload, headers=headers_b)
    assert put_cross_res.status_code in (403, 404), f"Expected 403/404 on update, got {put_cross_res.status_code}"
    print(f"✓ User B blocked from editing User A's invoice (HTTP {put_cross_res.status_code}).")

    # User A updates their own invoice -> 200 OK
    put_own_res = client.put(f"/api/invoices/{inv_a_id}", json={"vendorName": "Acme Cloud Services Updated"}, headers=headers_a)
    assert put_own_res.status_code == 200
    assert put_own_res.json()["vendorName"] == "Acme Cloud Services Updated"
    print("✓ User A successfully edited own invoice.")

    # 9. Secure Individual Endpoints: Delete
    # User B attempts to delete User A's invoice -> Must return 403 or 404
    del_cross_res = client.delete(f"/api/invoices/{inv_a_id}", headers=headers_b)
    assert del_cross_res.status_code in (403, 404), f"Expected 403/404 on delete, got {del_cross_res.status_code}"
    print(f"✓ User B blocked from deleting User A's invoice (HTTP {del_cross_res.status_code}).")

    # Verify invoice was NOT deleted
    get_after_unauth_del = client.get(f"/api/invoices/{inv_a_id}", headers=headers_a)
    assert get_after_unauth_del.status_code == 200
    print("✓ Confirmed User A's invoice still exists in database.")

    # User A deletes their own invoice -> 200 OK
    del_own_res = client.delete(f"/api/invoices/{inv_a_id}", headers=headers_a)
    assert del_own_res.status_code == 200
    print("✓ User A successfully deleted own invoice.")

    # Confirm it's now deleted
    get_after_del = client.get(f"/api/invoices/{inv_a_id}", headers=headers_a)
    assert get_after_del.status_code == 404
    print("✓ User A's invoice confirmed deleted (404).")

    print("\nALL MULTI-TENANCY & DATA ISOLATION TESTS PASSED PERFECTLY!\n")

if __name__ == "__main__":
    test_multi_tenancy()

