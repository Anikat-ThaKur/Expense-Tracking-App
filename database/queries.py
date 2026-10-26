from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    try:
        member_since = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    except (TypeError, ValueError):
        member_since = None

    return {"name": row["name"], "email": row["email"], "member_since": member_since}


def _date_filter(date_from, date_to):
    """Return the extra WHERE fragment and its bound params for an optional date range."""
    clause, params = "", []
    if date_from:
        clause += " AND date >= ?"
        params.append(date_from)
    if date_to:
        clause += " AND date <= ?"
        params.append(date_to)
    return clause, params


# ---- SECTION: summary stats (subagent 2) ---------------------------- #
def get_summary_stats(user_id, date_from=None, date_to=None):
    date_sql, date_params = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ?" + date_sql,
            (user_id, *date_params),
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?" + date_sql +
            " GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1",
            (user_id, *date_params),
        ).fetchone()
    finally:
        conn.close()

    if totals["cnt"] == 0 or top is None:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": round(totals["total"], 2),
        "transaction_count": totals["cnt"],
        "top_category": top["category"],
    }


# ---- SECTION: recent transactions (subagent 1) ---------------------- #
def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    date_sql, date_params = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + date_sql + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *date_params, limit),
        ).fetchall()
    finally:
        conn.close()

    return [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "amount": row["amount"],
        }
        for row in rows
    ]


# ---- SECTION: category breakdown (subagent 3) ----------------------- #
def get_category_breakdown(user_id, date_from=None, date_to=None):
    date_sql, date_params = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, ROUND(SUM(amount), 2) AS total "
            "FROM expenses WHERE user_id = ?" + date_sql +
            " GROUP BY category "
            "ORDER BY total DESC, category ASC",
            (user_id, *date_params),
        ).fetchall()
    finally:
        conn.close()

    grand_total = sum(row["total"] for row in rows)
    if not rows or grand_total <= 0:
        return []

    breakdown = [
        {
            "name": row["category"],
            "amount": row["total"],
            "pct": int(round(row["total"] * 100 / grand_total)),
        }
        for row in rows
    ]
    breakdown[0]["pct"] += 100 - sum(item["pct"] for item in breakdown)
    return breakdown
