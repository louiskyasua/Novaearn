import importlib
import os
from pathlib import Path


TEST_DB = Path(__file__).with_name("test_novaearn.db")
try:
    TEST_DB.unlink()
except FileNotFoundError:
    pass

os.environ["NOVA_EARN_SECRET"] = "test-secret-key-long-enough"
os.environ["NOVA_DB_PATH"] = str(TEST_DB)
os.environ["NOVA_DATA_DIR"] = str(TEST_DB.parent)
os.environ["FLASK_ENV"] = "testing"

app_module = importlib.import_module("app")


def test_app_imports():
    assert app_module.app is not None


def test_bank_api_exists():
    client = app_module.app.test_client()
    response = client.get("/api/banks")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert "banks" in payload
    assert isinstance(payload["banks"], list)


def test_referral_bonus_is_awarded_once_on_approved_deposit():
    c = app_module.db()
    c.execute("DELETE FROM transactions")
    c.execute("DELETE FROM deposits")
    c.execute("DELETE FROM users")
    c.execute(
        "INSERT INTO users(name,email,password,balance,referral_code,role) VALUES(?,?,?,?,?,?)",
        ("Referrer", "referrer@test.local", "x", 0, "REF001", "user"),
    )
    referrer_id = c.execute("SELECT id FROM users WHERE email=?", ("referrer@test.local",)).fetchone()[0]
    c.execute(
        "INSERT INTO users(name,email,password,balance,referral_code,referred_by,role) VALUES(?,?,?,?,?,?,?)",
        ("Referred", "referred@test.local", "x", 0, "REF002", referrer_id, "user"),
    )
    referred_id = c.execute("SELECT id FROM users WHERE email=?", ("referred@test.local",)).fetchone()[0]
    c.execute(
        "INSERT INTO deposits(user_id,amount,provider,reference,status,created_at) VALUES(?,?,?,?,?,datetime('now'))",
        (referred_id, 5000, "OPay", "TEST-REF-1", "pending"),
    )
    deposit_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.execute("UPDATE deposits SET status='approved' WHERE id=?", (deposit_id,))
    c.commit()

    balance = c.execute("SELECT balance FROM users WHERE id=?", (referrer_id,)).fetchone()[0]
    bonuses = c.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id=? AND kind='REFERRAL_BONUS'",
        (referrer_id,),
    ).fetchone()[0]
    assert balance == 500
    assert bonuses == 1

    c.execute("UPDATE deposits SET status='pending' WHERE id=?", (deposit_id,))
    c.execute("UPDATE deposits SET status='approved' WHERE id=?", (deposit_id,))
    c.commit()
    balance_again = c.execute("SELECT balance FROM users WHERE id=?", (referrer_id,)).fetchone()[0]
    bonuses_again = c.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id=? AND kind='REFERRAL_BONUS'",
        (referrer_id,),
    ).fetchone()[0]
    c.close()

    assert balance_again == 500
    assert bonuses_again == 1
