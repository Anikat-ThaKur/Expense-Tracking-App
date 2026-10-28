"""Tests for Step 7: Add Expense.

Based on .claude/specs/07-add-expense.md.
Uses an isolated temp SQLite DB; the real expense_tracker.db is never touched.
"""
import html
from datetime import date

import pytest
from werkzeug.security import generate_password_hash

import app as app_module
from database import db

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo1234"
CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Health", "Other"]

NEW_USER_EMAIL = "fresh@spendly.com"
NEW_USER_PASSWORD = "fresh1234"


# ---------------------------------------------------------------- fixtures

@pytest.fixture
def seeded(tmp_path, monkeypatch):
    """Isolated temp DB with seed data plus an empty second user."""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    db.seed_db()
    conn = db.get_db()
    try:
        demo_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()["id"]
        other_id = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Fresh", NEW_USER_EMAIL, generate_password_hash(NEW_USER_PASSWORD, method="pbkdf2:sha256")),
        ).lastrowid
        conn.commit()
    finally:
        conn.close()
    return demo_id, other_id


@pytest.fixture
def client(seeded):
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture
def auth_client(client):
    resp = client.post("/login", data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert resp.status_code == 302, "Demo login should redirect"
    return client


@pytest.fixture
def fresh_client(seeded):
    """Client logged in as the second (empty) user."""
    app_module.app.config["TESTING"] = True
    c = app_module.app.test_client()
    resp = c.post("/login", data={"email": NEW_USER_EMAIL, "password": NEW_USER_PASSWORD})
    assert resp.status_code == 302, "Fresh user login should redirect"
    return c


def today():
    return date.today().isoformat()


def valid_form(**overrides):
    data = {
        "amount": "23.50",
        "category": "Food",
        "description": "Test lunch",
        "date": today(),
    }
    data.update(overrides)
    return data


def all_expenses():
    conn = db.get_db()
    try:
        return conn.execute("SELECT * FROM expenses ORDER BY id").fetchall()
    finally:
        conn.close()


def count_expenses():
    return len(all_expenses())


# ---------------------------------------------------------------- auth guard

class TestAuthGuard:
    def test_get_logged_out_redirects_to_login(self, client):
        resp = client.get("/expenses/add")
        assert resp.status_code == 302, "Logged-out GET should redirect"
        assert "/login" in resp.headers["Location"], "Should redirect to /login"

    def test_post_logged_out_redirects_to_login(self, client):
        resp = client.post("/expenses/add", data=valid_form())
        assert resp.status_code == 302, "Logged-out POST should redirect"
        assert "/login" in resp.headers["Location"], "Should redirect to /login"

    def test_post_logged_out_saves_nothing(self, client):
        before = count_expenses()
        client.post("/expenses/add", data=valid_form())
        assert count_expenses() == before, "Logged-out POST must not create an expense"


# ---------------------------------------------------------------- GET form

class TestForm:
    def test_get_logged_in_returns_200(self, auth_client):
        resp = auth_client.get("/expenses/add")
        assert resp.status_code == 200

    def test_form_has_expected_fields(self, auth_client):
        body = auth_client.get("/expenses/add").get_data(as_text=True)
        for name in ("amount", "category", "description", "date"):
            assert f'name="{name}"' in body, f"Missing form field {name}"
        assert 'type="number"' in body
        assert 'step="0.01"' in body
        assert 'type="date"' in body

    def test_form_posts_and_has_cancel_link_to_profile(self, auth_client):
        body = auth_client.get("/expenses/add").get_data(as_text=True)
        assert "Cancel" in body, "Expected a Cancel link"
        assert 'href="/profile"' in body, "Cancel should link to /profile"

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_category_dropdown_lists_each_category(self, auth_client, category):
        body = auth_client.get("/expenses/add").get_data(as_text=True)
        assert "<select" in body
        assert f">{category}<" in body, f"Category {category} missing from dropdown"

    def test_category_dropdown_has_exactly_seven_options(self, auth_client):
        body = auth_client.get("/expenses/add").get_data(as_text=True)
        select = body[body.index("<select"):body.index("</select>")]
        assert select.count("<option") == 7, "Expected seven category options"

    def test_date_prefilled_with_today(self, auth_client):
        body = auth_client.get("/expenses/add").get_data(as_text=True)
        assert f'value="{today()}"' in body, "Date should default to today"

    def test_get_does_not_create_expense(self, auth_client):
        before = count_expenses()
        auth_client.get("/expenses/add")
        assert count_expenses() == before


# ---------------------------------------------------------------- happy path

class TestHappyPath:
    def test_valid_post_redirects_to_profile(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form())
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/profile"), "Should redirect to /profile"

    def test_valid_post_creates_row(self, auth_client):
        before = count_expenses()
        auth_client.post("/expenses/add", data=valid_form(description="Unique desc"))
        rows = all_expenses()
        assert len(rows) == before + 1, "Exactly one row should be added"
        row = rows[-1]
        assert row["amount"] == 23.50
        assert row["category"] == "Food"
        assert row["description"] == "Unique desc"
        assert row["date"] == today()

    def test_success_flash_shown_on_profile(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form(), follow_redirects=True)
        assert resp.status_code == 200
        assert "Expense added." in resp.get_data(as_text=True), "Expected success flash"

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_every_category_accepted(self, auth_client, category):
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=valid_form(category=category))
        assert resp.status_code == 302, f"{category} should be accepted"
        assert count_expenses() == before + 1
        assert all_expenses()[-1]["category"] == category

    def test_new_expense_visible_on_profile_with_rupee(self, fresh_client):
        fresh_client.post(
            "/expenses/add",
            data=valid_form(amount="777.25", description="Zebra purchase"),
        )
        body = html.unescape(fresh_client.get("/profile").get_data(as_text=True))
        assert "Zebra purchase" in body, "New expense should appear in recent transactions"
        assert "₹" in body, "Rupee symbol expected"
        assert "777.25" in body, "Amount should be displayed"

    def test_profile_totals_update_for_new_user(self, fresh_client):
        fresh_client.post("/expenses/add", data=valid_form(amount="100", category="Bills"))
        fresh_client.post("/expenses/add", data=valid_form(amount="50.50", category="Bills"))
        body = fresh_client.get("/profile").get_data(as_text=True)
        assert "150.50" in body, "Summary total should reflect new expenses"
        assert "Bills" in body, "Category breakdown should include Bills"

    def test_description_is_stripped(self, auth_client):
        auth_client.post("/expenses/add", data=valid_form(description="   padded   "))
        assert all_expenses()[-1]["description"] == "padded"


# ---------------------------------------------------------------- user_id

class TestUserId:
    def test_user_id_from_session(self, auth_client, seeded):
        demo_id, _ = seeded
        auth_client.post("/expenses/add", data=valid_form())
        assert all_expenses()[-1]["user_id"] == demo_id

    def test_user_id_in_form_is_ignored(self, auth_client, seeded):
        demo_id, other_id = seeded
        auth_client.post("/expenses/add", data=valid_form(user_id=str(other_id)))
        row = all_expenses()[-1]
        assert row["user_id"] == demo_id, "user_id must come from session, not form"
        assert row["user_id"] != other_id

    def test_second_user_expense_belongs_to_second_user(self, fresh_client, seeded):
        _, other_id = seeded
        fresh_client.post("/expenses/add", data=valid_form())
        assert all_expenses()[-1]["user_id"] == other_id


# ---------------------------------------------------------------- description / amount

class TestStorage:
    @pytest.mark.parametrize("desc", ["", "   "])
    def test_empty_description_stored_as_null(self, auth_client, desc):
        resp = auth_client.post("/expenses/add", data=valid_form(description=desc))
        assert resp.status_code == 302, "Empty description should be allowed"
        assert all_expenses()[-1]["description"] is None, "Empty description should be NULL"

    def test_missing_description_field_stored_as_null(self, auth_client):
        data = valid_form()
        del data["description"]
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 302
        assert all_expenses()[-1]["description"] is None

    @pytest.mark.parametrize(
        "raw,expected",
        [("12.345", 12.35), ("12.344", 12.34), ("5", 5.0), ("0.01", 0.01), ("1e2", 100.0)],
    )
    def test_amount_rounded_to_two_decimals(self, auth_client, raw, expected):
        resp = auth_client.post("/expenses/add", data=valid_form(amount=raw))
        assert resp.status_code == 302, f"{raw} should be valid"
        stored = all_expenses()[-1]["amount"]
        assert stored == pytest.approx(expected, abs=0.0051), f"{raw} stored as {stored}"
        assert round(stored, 2) == stored, "Stored amount must have at most 2 decimals"


# ---------------------------------------------------------------- validation

class TestValidation:
    @pytest.mark.parametrize(
        "amount",
        ["0", "0.00", "-5", "-0.01", "abc", "12abc", "", "   ", "nan", "NaN", "inf", "-inf", "Infinity"],
    )
    def test_invalid_amount_returns_400_and_saves_nothing(self, auth_client, amount):
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=valid_form(amount=amount))
        assert resp.status_code == 400, f"Amount {amount!r} should give 400"
        assert count_expenses() == before, f"Amount {amount!r} must not save"

    def test_missing_amount_returns_400(self, auth_client):
        data = valid_form()
        del data["amount"]
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 400
        assert count_expenses() == before

    @pytest.mark.parametrize(
        "category", ["Groceries", "food", "", "   ", "Food; DROP TABLE expenses;--", "' OR 1=1 --"]
    )
    def test_invalid_category_returns_400_and_saves_nothing(self, auth_client, category):
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=valid_form(category=category))
        assert resp.status_code == 400, f"Category {category!r} should give 400"
        assert count_expenses() == before

    def test_missing_category_returns_400(self, auth_client):
        data = valid_form()
        del data["category"]
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 400
        assert count_expenses() == before

    @pytest.mark.parametrize(
        "bad_date",
        ["", "not-a-date", "2026-13-01", "2026-02-30", "27-10-2026", "2026/10/27", "2026-1-5x", "2026-10-27 10:00"],
    )
    def test_malformed_date_returns_400_and_saves_nothing(self, auth_client, bad_date):
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=valid_form(date=bad_date))
        assert resp.status_code == 400, f"Date {bad_date!r} should give 400"
        assert count_expenses() == before

    def test_missing_date_returns_400(self, auth_client):
        data = valid_form()
        del data["date"]
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=data)
        assert resp.status_code == 400
        assert count_expenses() == before

    def test_error_response_shows_form_again(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form(amount="-1"))
        body = resp.get_data(as_text=True)
        assert resp.status_code == 400
        assert 'name="amount"' in body, "Form should be re-rendered on error"
        assert "<select" in body

    def test_error_response_contains_error_message(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form(amount="0"))
        body = resp.get_data(as_text=True).lower()
        assert "error" in body or "invalid" in body or "must" in body or "greater" in body, (
            "Expected a visible error message"
        )

    def test_sql_injection_in_description_stored_literally(self, auth_client):
        payload = "x'); DROP TABLE expenses;--"
        resp = auth_client.post("/expenses/add", data=valid_form(description=payload))
        assert resp.status_code == 302
        assert all_expenses()[-1]["description"] == payload, "Parameterised query should store text literally"

    def test_very_long_description_does_not_crash(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form(description="a" * 5000))
        assert resp.status_code in (302, 400), "Long description must not cause a 500"

    def test_description_over_200_chars_rejected(self, auth_client):
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=valid_form(description="a" * 201))
        assert resp.status_code == 400
        assert count_expenses() == before

    def test_description_of_200_chars_accepted(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form(description="a" * 200))
        assert resp.status_code == 302

    @pytest.mark.parametrize("amount", ["10000000.01", "1e308", "99999999999"])
    def test_amount_above_maximum_rejected(self, auth_client, amount):
        before = count_expenses()
        resp = auth_client.post("/expenses/add", data=valid_form(amount=amount))
        assert resp.status_code == 400
        assert count_expenses() == before

    def test_amount_at_maximum_accepted(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form(amount="10000000"))
        assert resp.status_code == 302

    def test_description_input_has_maxlength(self, auth_client):
        assert 'maxlength="200"' in auth_client.get("/expenses/add").get_data(as_text=True)


# ---------------------------------------------------------------- retained values

class TestFormRetention:
    def test_values_retained_after_error(self, auth_client):
        resp = auth_client.post(
            "/expenses/add",
            data={
                "amount": "-42.5",
                "category": "Health",
                "description": "Retained note",
                "date": "2026-03-04",
            },
        )
        body = resp.get_data(as_text=True)
        assert resp.status_code == 400
        assert "-42.5" in body, "Amount should be retained"
        assert "Retained note" in body, "Description should be retained"
        assert "2026-03-04" in body, "Date should be retained"
        select = body[body.index("<select"):body.index("</select>")]
        health_option = [ln for ln in select.splitlines() if ">Health<" in ln]
        assert health_option and "selected" in health_option[0], "Category should stay selected"

    def test_non_numeric_amount_retained(self, auth_client):
        resp = auth_client.post("/expenses/add", data=valid_form(amount="abc"))
        assert resp.status_code == 400
        assert 'value="abc"' in resp.get_data(as_text=True), "Typed amount should be retained"

    def test_malformed_date_retained(self, auth_client):
        resp = auth_client.post(
            "/expenses/add", data=valid_form(date="2026-99-99", description="keepme")
        )
        body = resp.get_data(as_text=True)
        assert resp.status_code == 400
        assert "keepme" in body

    def test_retained_description_is_html_escaped(self, auth_client):
        resp = auth_client.post(
            "/expenses/add",
            data=valid_form(amount="0", description='<script>alert(1)</script>'),
        )
        body = resp.get_data(as_text=True)
        assert "<script>alert(1)</script>" not in body, "User input must be escaped"


# ---------------------------------------------------------------- profile entry point / cancel

class TestProfileIntegration:
    def test_profile_links_to_add_expense(self, auth_client):
        body = auth_client.get("/profile").get_data(as_text=True)
        assert "/expenses/add" in body, "Profile should link to the add-expense form"

    def test_following_profile_link_works(self, auth_client):
        resp = auth_client.get("/expenses/add")
        assert resp.status_code == 200

    def test_cancel_path_creates_no_expense(self, auth_client):
        before = count_expenses()
        auth_client.get("/expenses/add")
        resp = auth_client.get("/profile")
        assert resp.status_code == 200
        assert count_expenses() == before


# ---------------------------------------------------------------- placeholders unchanged

class TestPlaceholdersUnchanged:
    def test_edit_placeholder_unchanged(self, auth_client):
        resp = auth_client.get("/expenses/1/edit")
        assert resp.status_code == 200
        assert "Step 8" in resp.get_data(as_text=True), "Edit placeholder should mention Step 8"

    def test_delete_placeholder_unchanged(self, auth_client):
        resp = auth_client.get("/expenses/1/delete")
        assert resp.status_code == 200
        assert "Step 9" in resp.get_data(as_text=True), "Delete placeholder should mention Step 9"

    def test_placeholders_do_not_modify_data(self, auth_client):
        before = all_expenses()
        auth_client.get("/expenses/1/edit")
        auth_client.get("/expenses/1/delete")
        assert len(all_expenses()) == len(before), "Delete placeholder must not delete anything"
