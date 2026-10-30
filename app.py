import math
import os
import sqlite3
from datetime import date, datetime

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from database.date_ranges import (
    active_preset_key,
    filter_presets,
    resolve_date_range,
)
from database.constants import (
    EXPENSE_CATEGORIES,
    MAX_DESCRIPTION_LENGTH,
    MAX_EXPENSE_AMOUNT,
)
from database.db import get_db, init_db, seed_db
from database.queries import (
    create_expense,
    delete_expense_by_id,
    get_category_breakdown,
    get_expense_by_id,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
    update_expense,
)

app = Flask(__name__)
# The fallback is for local development only; set SECRET_KEY in any real deployment.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")


def _validate_expense_form(form):
    """Return (values, error): the stripped form input, and a message or None if valid."""
    values = {
        "amount": form.get("amount", "").strip(),
        "category": form.get("category", "").strip(),
        "description": form.get("description", "").strip(),
        "date": form.get("date", "").strip(),
    }

    try:
        amount = float(values["amount"])
    except ValueError:
        amount = None
    if (
        amount is None
        or not math.isfinite(amount)
        or amount <= 0
        or amount > MAX_EXPENSE_AMOUNT
    ):
        return (
            values,
            f"Amount must be a number greater than 0 and at most {MAX_EXPENSE_AMOUNT:,}.",
        )

    if values["category"] not in EXPENSE_CATEGORIES:
        return values, "Please choose a valid category."

    try:
        datetime.strptime(values["date"], "%Y-%m-%d")
    except ValueError:
        return values, "Please enter a valid date."

    if len(values["description"]) > MAX_DESCRIPTION_LENGTH:
        return (
            values,
            f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer.",
        )

    return values, None


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    error = None
    if not name:
        error = "Please enter your name."
    elif not email or "@" not in email:
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."

    if error:
        return (
            render_template("register.html", error=error, name=name, email=email),
            400,
        )

    password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return (
            render_template(
                "register.html",
                error="An account with that email already exists.",
                name=name,
                email=email,
            ),
            400,
        )
    finally:
        conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return (
            render_template(
                "login.html", error="Please enter your email and password.", email=email
            ),
            400,
        )

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return (
            render_template(
                "login.html", error="Invalid email or password.", email=email
            ),
            401,
        )

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    date_from, date_to, error = resolve_date_range(
        request.args.get("date_from", "").strip(),
        request.args.get("date_to", "").strip(),
    )
    if error:
        flash(error)

    presets = filter_presets(date.today())

    return render_template(
        "profile.html",
        user=user,
        stats=get_summary_stats(user_id, date_from=date_from, date_to=date_to),
        breakdown=get_category_breakdown(user_id, date_from=date_from, date_to=date_to),
        recent=get_recent_transactions(user_id, date_from=date_from, date_to=date_to),
        presets=presets,
        active_preset=active_preset_key(presets, date_from, date_to),
        date_from=date_from,
        date_to=date_to,
    )


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    return render_template("analytics.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=EXPENSE_CATEGORIES,
            form={"date": date.today().isoformat()},
            form_action=url_for("add_expense"),
        )

    values, error = _validate_expense_form(request.form)
    if error:
        return (
            render_template(
                "add_expense.html",
                error=error,
                categories=EXPENSE_CATEGORIES,
                form=values,
                form_action=url_for("add_expense"),
            ),
            400,
        )

    create_expense(
        user_id,
        amount=round(float(values["amount"]), 2),
        category=values["category"],
        description=values["description"] or None,
        expense_date=values["date"],
    )
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    expense = get_expense_by_id(user_id, id)
    if expense is None:
        abort(404)

    edit_context = {
        "categories": EXPENSE_CATEGORIES,
        "form_action": url_for("edit_expense", id=id),
        "page_title": "Edit expense",
        "page_subtitle": "Update the details",
        "submit_label": "Save changes",
    }

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            form={
                "amount": f"{expense['amount']:.2f}",
                "category": expense["category"],
                "description": expense["description"] or "",
                "date": expense["date"],
            },
            **edit_context,
        )

    values, error = _validate_expense_form(request.form)
    if error:
        return (
            render_template(
                "add_expense.html", error=error, form=values, **edit_context
            ),
            400,
        )

    updated = update_expense(
        user_id,
        id,
        amount=round(float(values["amount"]), 2),
        category=values["category"],
        description=values["description"] or None,
        expense_date=values["date"],
    )
    if not updated:
        abort(404)

    flash("Expense updated.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    if not delete_expense_by_id(user_id, id):
        abort(404)

    flash("Expense deleted.", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    init_db()
    seed_db()
    app.run(debug=True, port=5001)
