import pytest

import app as app_module
from database import db, queries


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    conn = db.get_db()
    try:
        user_id = conn.execute("SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)).fetchone()["id"]
        empty_id = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES ('Empty', 'empty@x.com', 'x')"
        ).lastrowid
        conn.commit()
    finally:
        conn.close()
    return user_id, empty_id


@pytest.fixture
def client(seeded):
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def login(client, email="demo@spendly.com", password="demo1234"):
    return client.post("/login", data={"email": email, "password": password})


def test_get_user_by_id(seeded):
    user = queries.get_user_by_id(seeded[0])
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert user["member_since"]


def test_get_user_by_id_missing(seeded):
    assert queries.get_user_by_id(9999) is None


def test_summary_stats(seeded):
    stats = queries.get_summary_stats(seeded[0])
    assert stats == {"total_spent": 381.64, "transaction_count": 8, "top_category": "Bills"}


def test_summary_stats_empty(seeded):
    assert queries.get_summary_stats(seeded[1]) == {
        "total_spent": 0, "transaction_count": 0, "top_category": "—",
    }


def test_recent_transactions(seeded):
    rows = queries.get_recent_transactions(seeded[0])
    assert len(rows) == 8
    assert set(rows[0]) == {"date", "description", "category", "amount"}
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates, reverse=True)


def test_recent_transactions_empty(seeded):
    assert queries.get_recent_transactions(seeded[1]) == []


def test_category_breakdown(seeded):
    rows = queries.get_category_breakdown(seeded[0])
    assert len(rows) == 6
    amounts = [r["amount"] for r in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(r["pct"], int) for r in rows)
    assert sum(r["pct"] for r in rows) == 100


def test_category_breakdown_empty(seeded):
    assert queries.get_category_breakdown(seeded[1]) == []


def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_profile_authenticated(client):
    login(client)
    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Demo User" in html and "demo@spendly.com" in html
    assert "₹381.64" in html
    assert "Bills" in html
    assert html.index("2026-10-18") < html.index("2026-10-01")
    assert html.count('class="category-bar"') == 6


def test_profile_new_user_empty(client):
    client.post("/register", data={"name": "New", "email": "new@x.com", "password": "password1"})
    login(client, "new@x.com", "password1")
    resp = client.get("/profile")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "₹0.00" in html
    assert "No expenses yet" in html
