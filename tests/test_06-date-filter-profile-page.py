"""Tests for Step 6: Date Filter for the Profile page.

Based on .claude/specs/06-date-filter-profile-page.md.

Seed data (demo@spendly.com, 8 expenses, total 381.64):
    2026-10-01 Food          45.50  Groceries
    2026-10-02 Transport     12.00  Metro card top-up
    2026-10-05 Shopping      89.99  Running shoes
    2026-10-07 Food          15.75  Lunch with team
    2026-10-10 Bills        120.00  Electricity bill
    2026-10-12 Entertainment 30.00  Movie night
    2026-10-15 Food           8.40  Coffee and pastry
    2026-10-18 Health        60.00  Pharmacy
"""
import re
from datetime import date, timedelta

import pytest

import app as app_module
from database import db, queries

DEMO_EMAIL = "demo@spendly.com"
DEMO_PASSWORD = "demo1234"

# Range 2026-10-05 .. 2026-10-12 (inclusive) covers 4 seed rows.
RANGE_FROM = "2026-10-05"
RANGE_TO = "2026-10-12"
RANGE_TOTAL = 255.74  # 89.99 + 15.75 + 120.00 + 30.00
RANGE_DESCRIPTIONS_IN = ["Running shoes", "Lunch with team", "Electricity bill", "Movie night"]
RANGE_DESCRIPTIONS_OUT = ["Groceries", "Metro card top-up", "Coffee and pastry", "Pharmacy"]

PRESET_LABELS = ["This Month", "Last 3 Months", "Last 6 Months", "All Time"]


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
            ("Other", "other@x.com", "x"),
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


def add_expense(user_id, amount, category, description, day):
    conn = db.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, description, date) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, description, day),
        )
        conn.commit()
    finally:
        conn.close()


def get_html(client, **params):
    resp = client.get("/profile", query_string=params)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    return resp.get_data(as_text=True)


def find_anchor(html, label):
    """Return the full <a ...>label</a> element text for a link containing label."""
    for m in re.finditer(r"<a\b[^>]*>.*?</a>", html, re.S):
        if label in re.sub(r"<[^>]+>", "", m.group(0)):
            return m.group(0)
    return None


def anchor_href(anchor):
    m = re.search(r'href="([^"]*)"', anchor)
    assert m, f"Anchor has no href: {anchor}"
    return m.group(1).replace("&amp;", "&")


def anchor_is_active(anchor):
    opening = re.match(r"<a\b[^>]*>", anchor).group(0)
    return "active" in opening or "aria-current" in opening


# ------------------------------------------------------------- auth guard

class TestAuthGuard:
    def test_profile_with_filter_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/profile", query_string={"date_from": RANGE_FROM, "date_to": RANGE_TO})
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_profile_with_malformed_filter_unauthenticated_redirects_to_login(self, client):
        resp = client.get("/profile?date_from=garbage&date_to=junk")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------- unfiltered view

class TestUnfiltered:
    def test_no_params_shows_all_expenses_and_total(self, auth_client):
        html = get_html(auth_client)
        assert "₹381.64" in html
        for desc in RANGE_DESCRIPTIONS_IN + RANGE_DESCRIPTIONS_OUT:
            assert desc in html, f"{desc} should be visible when unfiltered"

    def test_no_params_all_time_preset_is_active(self, auth_client):
        html = get_html(auth_client)
        anchor = find_anchor(html, "All Time")
        assert anchor is not None
        assert anchor_is_active(anchor), "All Time should be highlighted by default"

    def test_no_params_other_presets_not_active(self, auth_client):
        html = get_html(auth_client)
        for label in ["This Month", "Last 3 Months", "Last 6 Months"]:
            anchor = find_anchor(html, label)
            assert anchor is not None
            assert not anchor_is_active(anchor), f"{label} should not be active"


# -------------------------------------------------------- filter bar markup

class TestFilterBar:
    def test_all_four_preset_labels_present(self, auth_client):
        html = get_html(auth_client)
        for label in PRESET_LABELS:
            assert label in html, f"Missing preset '{label}'"

    def test_two_date_inputs_and_apply_button(self, auth_client):
        html = get_html(auth_client)
        assert re.search(r'<input[^>]*type="date"[^>]*name="date_from"|'
                         r'<input[^>]*name="date_from"[^>]*type="date"', html)
        assert re.search(r'<input[^>]*type="date"[^>]*name="date_to"|'
                         r'<input[^>]*name="date_to"[^>]*type="date"', html)
        assert "Apply" in html

    def test_all_time_link_is_clean_profile_url(self, auth_client):
        html = get_html(auth_client)
        href = anchor_href(find_anchor(html, "All Time"))
        assert href.rstrip("/").endswith("/profile")
        assert "?" not in href, "All Time must not carry query params"

    def test_this_month_link_params(self, auth_client):
        today = date.today()
        href = anchor_href(find_anchor(get_html(auth_client), "This Month"))
        assert f"date_from={today.replace(day=1).isoformat()}" in href
        assert f"date_to={today.isoformat()}" in href

    @pytest.mark.parametrize("label", ["Last 3 Months", "Last 6 Months"])
    def test_multi_month_links_end_today_and_start_in_past(self, auth_client, label):
        today = date.today()
        href = anchor_href(find_anchor(get_html(auth_client), label))
        assert f"date_to={today.isoformat()}" in href
        m = re.search(r"date_from=(\d{4}-\d{2}-\d{2})", href)
        assert m, f"{label} link should carry date_from"
        start = date.fromisoformat(m.group(1))
        days = (today - start).days
        low, high = (89, 93) if "3" in label else (180, 185)
        assert low <= days <= high, f"{label} window of {days} days looks wrong"

    def test_custom_range_prefills_date_inputs(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        assert f'value="{RANGE_FROM}"' in html
        assert f'value="{RANGE_TO}"' in html

    def test_custom_range_does_not_activate_any_preset(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        for label in PRESET_LABELS:
            assert not anchor_is_active(find_anchor(html, label)), (
                f"{label} should not be active for a custom range"
            )


# ------------------------------------------------------------ custom ranges

class TestCustomRange:
    def test_stats_respect_range(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        assert f"₹{RANGE_TOTAL:.2f}" in html
        assert "₹381.64" not in html

    def test_transactions_respect_range(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        for desc in RANGE_DESCRIPTIONS_IN:
            assert desc in html, f"{desc} should be in range"
        for desc in RANGE_DESCRIPTIONS_OUT:
            assert desc not in html, f"{desc} should be excluded"

    def test_category_breakdown_respects_range(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        # Shopping, Food, Bills, Entertainment
        assert html.count('class="category-bar"') == 4

    def test_bounds_are_inclusive_single_day(self, auth_client):
        html = get_html(auth_client, date_from="2026-10-10", date_to="2026-10-10")
        assert "Electricity bill" in html
        assert "₹120.00" in html
        assert "Movie night" not in html and "Lunch with team" not in html

    def test_equal_dates_do_not_flash_error(self, auth_client):
        html = get_html(auth_client, date_from="2026-10-10", date_to="2026-10-10")
        assert "Start date must be before end date." not in html

    def test_rupee_symbol_with_filter(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        assert html.count("₹") >= 5, "Total, transaction amounts and breakdown should show ₹"
        assert "$" not in html.split('class="expense-list"')[-1], "No $ currency symbol expected"

    def test_transaction_count_in_stats_respects_range(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        # four rows rendered in the transaction list
        listing = html[html.index('class="expense-list"'):]
        for desc in RANGE_DESCRIPTIONS_IN:
            assert desc in listing


# ----------------------------------------------------- presets (relative)

class TestPresets:
    @pytest.fixture
    def preset_user(self, client, seeded):
        """Fresh user whose expenses are placed relative to today."""
        client.post("/register", data={"name": "Pre", "email": "pre@x.com", "password": "password1"})
        client.post("/login", data={"email": "pre@x.com", "password": "password1"})
        conn = db.get_db()
        uid = conn.execute("SELECT id FROM users WHERE email = ?", ("pre@x.com",)).fetchone()["id"]
        conn.close()
        today = date.today()
        add_expense(uid, 11.00, "Food", "PRESET-TODAY", today.isoformat())
        add_expense(uid, 22.00, "Bills", "PRESET-45D", (today - timedelta(days=45)).isoformat())
        add_expense(uid, 33.00, "Health", "PRESET-120D", (today - timedelta(days=120)).isoformat())
        add_expense(uid, 44.00, "Travel", "PRESET-250D", (today - timedelta(days=250)).isoformat())
        return client

    def _visit_preset(self, client, label):
        html = get_html(client)
        href = anchor_href(find_anchor(html, label))
        resp = client.get(href)
        assert resp.status_code == 200
        return resp.get_data(as_text=True)

    @staticmethod
    def _present(html):
        return {k for k in ["TODAY", "45D", "120D", "250D"] if f"PRESET-{k}" in html}

    def test_this_month_only_current_month(self, preset_user):
        html = self._visit_preset(preset_user, "This Month")
        assert self._present(html) == {"TODAY"}

    def test_last_3_months_window(self, preset_user):
        html = self._visit_preset(preset_user, "Last 3 Months")
        assert self._present(html) == {"TODAY", "45D"}

    def test_last_6_months_window(self, preset_user):
        html = self._visit_preset(preset_user, "Last 6 Months")
        assert self._present(html) == {"TODAY", "45D", "120D"}

    def test_all_time_shows_everything(self, preset_user):
        html = self._visit_preset(preset_user, "All Time")
        assert self._present(html) == {"TODAY", "45D", "120D", "250D"}
        assert "₹110.00" in html

    @pytest.mark.parametrize("label", ["This Month", "Last 3 Months", "Last 6 Months", "All Time"])
    def test_clicked_preset_is_highlighted_exclusively(self, preset_user, label):
        html = self._visit_preset(preset_user, label)
        for other in PRESET_LABELS:
            active = anchor_is_active(find_anchor(html, other))
            assert active == (other == label), (
                f"After clicking '{label}', active state of '{other}' was {active}"
            )

    def test_this_month_totals_match_filter(self, preset_user):
        html = self._visit_preset(preset_user, "This Month")
        assert "₹11.00" in html
        assert "₹110.00" not in html


# ------------------------------------------------------- validation errors

class TestInvalidInput:
    FLASH = "Start date must be before end date."

    def test_start_after_end_flashes_error(self, auth_client):
        html = get_html(auth_client, date_from="2026-10-18", date_to="2026-10-01")
        assert self.FLASH in html

    def test_start_after_end_falls_back_to_unfiltered(self, auth_client):
        html = get_html(auth_client, date_from="2026-10-18", date_to="2026-10-01")
        assert "₹381.64" in html
        for desc in RANGE_DESCRIPTIONS_IN + RANGE_DESCRIPTIONS_OUT:
            assert desc in html

    def test_start_after_end_highlights_all_time(self, auth_client):
        html = get_html(auth_client, date_from="2026-10-18", date_to="2026-10-01")
        assert anchor_is_active(find_anchor(html, "All Time"))

    def test_no_flash_on_valid_request(self, auth_client):
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        assert self.FLASH not in html

    @pytest.mark.parametrize("params", [
        {"date_from": "not-a-date", "date_to": RANGE_TO},
        {"date_from": RANGE_FROM, "date_to": "not-a-date"},
        {"date_from": "not-a-date", "date_to": "also-bad"},
        {"date_from": "2026-13-01", "date_to": RANGE_TO},
        {"date_from": "2026-02-30", "date_to": RANGE_TO},
        {"date_from": "10/05/2026", "date_to": "10/12/2026"},
        {"date_from": "", "date_to": ""},
        {"date_from": "   ", "date_to": "   "},
        {"date_from": "99999-01-01", "date_to": RANGE_TO},
    ])
    def test_malformed_dates_fall_back_to_unfiltered(self, auth_client, params):
        html = get_html(auth_client, **params)
        assert "₹381.64" in html, f"Expected unfiltered view for {params}"
        assert "Pharmacy" in html and "Groceries" in html

    @pytest.mark.parametrize("params", [
        {"date_from": RANGE_FROM},
        {"date_to": RANGE_TO},
    ])
    def test_only_one_date_falls_back_to_unfiltered(self, auth_client, params):
        html = get_html(auth_client, **params)
        assert "₹381.64" in html
        assert "Pharmacy" in html and "Groceries" in html

    def test_unknown_extra_params_ignored(self, auth_client):
        html = get_html(auth_client, foo="bar", date_from=RANGE_FROM, date_to=RANGE_TO)
        assert f"₹{RANGE_TOTAL:.2f}" in html

    @pytest.mark.parametrize("payload", [
        "2026-01-01' OR '1'='1",
        "'; DROP TABLE expenses;--",
        "2026-10-01\" OR 1=1 --",
        "1; DELETE FROM expenses",
        "<script>alert(1)</script>",
    ])
    def test_sql_injection_input_is_harmless(self, auth_client, seeded, payload):
        resp = auth_client.get("/profile", query_string={"date_from": payload, "date_to": RANGE_TO})
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "₹381.64" in html, "Malformed input should yield unfiltered view"
        assert "<script>alert(1)</script>" not in html, "Input must not be reflected unescaped"
        conn = db.get_db()
        try:
            count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()
        assert count == 8, "Expenses table must be intact"

    @pytest.mark.parametrize("payload", [
        "2026-01-01' OR '1'='1",
        "'; DROP TABLE expenses;--",
    ])
    def test_sql_injection_in_query_helpers_is_safe(self, seeded, payload):
        uid = seeded[0]
        queries.get_summary_stats(uid, payload, payload)
        queries.get_recent_transactions(uid, date_from=payload, date_to=payload)
        queries.get_category_breakdown(uid, payload, payload)
        conn = db.get_db()
        try:
            count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
        finally:
            conn.close()
        assert count == 8


# ------------------------------------------------------------ empty range

class TestEmptyRange:
    def test_empty_range_zero_state(self, auth_client):
        html = get_html(auth_client, date_from="2020-01-01", date_to="2020-12-31")
        assert "₹0.00" in html
        assert "Groceries" not in html and "Pharmacy" not in html
        assert 'class="category-bar"' not in html

    def test_empty_range_helpers(self, seeded):
        uid = seeded[0]
        assert queries.get_summary_stats(uid, "2020-01-01", "2020-12-31") == {
            "total_spent": 0, "transaction_count": 0, "top_category": "—",
        }
        assert queries.get_recent_transactions(uid, date_from="2020-01-01", date_to="2020-12-31") == []
        assert queries.get_category_breakdown(uid, "2020-01-01", "2020-12-31") == []

    def test_user_without_expenses_with_filter(self, client):
        client.post("/register", data={"name": "N", "email": "n@x.com", "password": "password1"})
        client.post("/login", data={"email": "n@x.com", "password": "password1"})
        html = get_html(client, date_from=RANGE_FROM, date_to=RANGE_TO)
        assert "₹0.00" in html


# --------------------------------------------------------- query helpers

class TestQueryHelpers:
    def test_summary_stats_no_dates_unchanged(self, seeded):
        assert queries.get_summary_stats(seeded[0]) == {
            "total_spent": 381.64, "transaction_count": 8, "top_category": "Bills",
        }

    def test_summary_stats_with_range(self, seeded):
        stats = queries.get_summary_stats(seeded[0], RANGE_FROM, RANGE_TO)
        assert stats["total_spent"] == pytest.approx(RANGE_TOTAL)
        assert stats["transaction_count"] == 4
        assert stats["top_category"] == "Bills"

    def test_summary_stats_top_category_changes_with_range(self, seeded):
        stats = queries.get_summary_stats(seeded[0], "2026-10-01", "2026-10-02")
        assert stats["transaction_count"] == 2
        assert stats["total_spent"] == pytest.approx(57.50)
        assert stats["top_category"] == "Food"

    def test_summary_stats_bounds_inclusive(self, seeded):
        stats = queries.get_summary_stats(seeded[0], "2026-10-01", "2026-10-18")
        assert stats["transaction_count"] == 8
        assert stats["total_spent"] == pytest.approx(381.64)

    def test_summary_stats_single_day_bound(self, seeded):
        stats = queries.get_summary_stats(seeded[0], "2026-10-18", "2026-10-18")
        assert stats == {"total_spent": 60.0, "transaction_count": 1, "top_category": "Health"}

    def test_recent_transactions_with_range(self, seeded):
        rows = queries.get_recent_transactions(seeded[0], date_from=RANGE_FROM, date_to=RANGE_TO)
        assert [r["description"] for r in rows] == [
            "Movie night", "Electricity bill", "Lunch with team", "Running shoes",
        ]
        dates = [r["date"] for r in rows]
        assert dates == sorted(dates, reverse=True)
        assert RANGE_FROM in dates and RANGE_TO in dates, "Bounds must be inclusive"

    def test_recent_transactions_no_dates_unchanged(self, seeded):
        assert len(queries.get_recent_transactions(seeded[0])) == 8

    def test_recent_transactions_limit_still_applies_with_filter(self, seeded):
        uid = seeded[0]
        for i in range(12):
            add_expense(uid, 1.00, "Misc", f"bulk-{i}", "2025-05-%02d" % (i + 1))
        rows = queries.get_recent_transactions(uid, date_from="2025-05-01", date_to="2025-05-31")
        assert len(rows) == 10
        assert rows[0]["description"] == "bulk-11"
        rows3 = queries.get_recent_transactions(uid, limit=3, date_from="2025-05-01", date_to="2025-05-31")
        assert len(rows3) == 3

    def test_category_breakdown_with_range(self, seeded):
        rows = queries.get_category_breakdown(seeded[0], RANGE_FROM, RANGE_TO)
        by_cat = {r["name"] if "name" in r else r["category"]: r for r in rows}
        assert set(by_cat) == {"Bills", "Shopping", "Food", "Entertainment"}
        amounts = [r["amount"] for r in rows]
        assert amounts == sorted(amounts, reverse=True)
        assert all(isinstance(r["pct"], int) for r in rows)
        assert 99 <= sum(r["pct"] for r in rows) <= 101

    def test_category_breakdown_percentages_recalculated(self, seeded):
        rows = queries.get_category_breakdown(seeded[0], "2026-10-01", "2026-10-01")
        assert len(rows) == 1
        assert rows[0]["pct"] == 100
        assert rows[0]["amount"] == pytest.approx(45.50)

    def test_category_breakdown_no_dates_unchanged(self, seeded):
        assert len(queries.get_category_breakdown(seeded[0])) == 6

    def test_helpers_scoped_per_user_with_filter(self, seeded):
        demo_id, other_id = seeded
        add_expense(other_id, 999.00, "Travel", "OTHER-USER-TRIP", "2026-10-08")

        stats = queries.get_summary_stats(demo_id, RANGE_FROM, RANGE_TO)
        assert stats["total_spent"] == pytest.approx(RANGE_TOTAL)
        assert stats["transaction_count"] == 4

        descs = [r["description"] for r in
                 queries.get_recent_transactions(demo_id, date_from=RANGE_FROM, date_to=RANGE_TO)]
        assert "OTHER-USER-TRIP" not in descs

        cats = [r for r in queries.get_category_breakdown(demo_id, RANGE_FROM, RANGE_TO)]
        assert len(cats) == 4

        other_stats = queries.get_summary_stats(other_id, RANGE_FROM, RANGE_TO)
        assert other_stats["total_spent"] == pytest.approx(999.00)
        assert other_stats["transaction_count"] == 1

    def test_profile_does_not_leak_other_users_expenses_under_filter(self, auth_client, seeded):
        add_expense(seeded[1], 999.00, "Travel", "OTHER-USER-TRIP", "2026-10-08")
        html = get_html(auth_client, date_from=RANGE_FROM, date_to=RANGE_TO)
        assert "OTHER-USER-TRIP" not in html
        assert f"₹{RANGE_TOTAL:.2f}" in html
