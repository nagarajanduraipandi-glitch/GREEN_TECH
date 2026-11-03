import calendar
import math
import os
import re
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

from database import queries
from database.db import (
    CATEGORIES,
    create_user,
    get_db,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
# Dev-only fallback key; set SECRET_KEY in the environment before deploying.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
# Browsers will not send the session cookie on cross-site POSTs (CSRF mitigation).
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
DUMMY_HASH = generate_password_hash("not-a-real-password")

with app.app_context():
    init_db()
    seed_db()


def get_today():
    return date.today()


def add_months(d, months):
    """Move d back by whole calendar months, clamping to the last day of the month."""
    index = d.year * 12 + (d.month - 1) - months
    year, month = divmod(index, 12)
    month += 1
    return d.replace(
        year=year, month=month, day=min(d.day, calendar.monthrange(year, month)[1])
    )


def parse_date(value):
    """Return value if it is a valid YYYY-MM-DD date, else None."""
    try:
        datetime.strptime(value or "", "%Y-%m-%d")
    except ValueError:
        return None
    return value


def build_presets(today):
    return [
        ("This Month", today.replace(day=1).isoformat(), today.isoformat()),
        ("Last 3 Months", add_months(today, 3).isoformat(), today.isoformat()),
        ("Last 6 Months", add_months(today, 6).isoformat(), today.isoformat()),
    ]


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": get_user_by_id(user_id) if user_id else None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    if request.method != "POST":
        abort(405)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    error = None
    if not (name and email and password and confirm_password):
        error = "All fields are required."
    elif password != confirm_password:
        error = "Passwords do not match."
    elif len(password) < MIN_PASSWORD_LENGTH:
        error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    elif not EMAIL_RE.match(email):
        error = "Enter a valid email address."

    if error is None:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            error = "Email already registered."

    if error:
        flash(error, "error")
        return render_template("register.html", name=name, email=email)

    flash("Account created. Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "GET":
        return render_template("login.html")
    if request.method != "POST":
        abort(405)

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email) if email else None
    # Hash against a dummy when the user is unknown so timing does not leak it.
    password_hash = user["password_hash"] if user else DUMMY_HASH
    if not (check_password_hash(password_hash, password) and user and password):
        flash("Invalid email or password.", "error")
        return render_template("login.html", email=email)

    session.clear()
    session["user_id"] = user["id"]
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = queries.get_user_by_id(user_id)
    if user is None:
        # The session points at a user that no longer exists.
        session.clear()
        return redirect(url_for("login"))
    user["initials"] = "".join(w[0] for w in user["name"].split()[:2]).upper()

    date_from = parse_date(request.args.get("date_from"))
    date_to = parse_date(request.args.get("date_to"))
    if not (date_from and date_to):
        date_from = date_to = None
    elif date_from > date_to:
        flash("Start date must be before end date.", "error")
        date_from = date_to = None

    presets = [
        {
            "label": label,
            "url": url_for("profile", date_from=start, date_to=end),
            "active": (date_from, date_to) == (start, end),
        }
        for label, start, end in build_presets(get_today())
    ]
    no_filter = date_from is None
    presets.append(
        {"label": "All Time", "url": url_for("profile"), "active": no_filter}
    )
    custom_active = not no_filter and not any(p["active"] for p in presets)

    return render_template(
        "profile.html",
        user=user,
        stats=queries.get_summary_stats(user_id, date_from, date_to),
        expenses=queries.get_recent_transactions(
            user_id, date_from=date_from, date_to=date_to
        ),
        breakdown=queries.get_category_breakdown(user_id, date_from, date_to),
        presets=presets,
        date_from=date_from,
        date_to=date_to,
        custom_active=custom_active,
    )


MAX_AMOUNT = 10_000_000
MAX_DESCRIPTION_LENGTH = 200


def validate_expense_form(form):
    """Return (values, error); values holds the cleaned fields when error is None."""
    raw_amount = form.get("amount", "").strip()
    category = form.get("category", "")
    raw_date = form.get("date", "").strip()
    description = form.get("description", "").strip()

    if not raw_amount:
        return None, "Amount is required."
    try:
        amount = float(raw_amount)
    except ValueError:
        return None, "Enter a valid amount greater than 0."
    if not math.isfinite(amount) or amount <= 0:
        return None, "Enter a valid amount greater than 0."
    if amount > MAX_AMOUNT:
        return None, "Amount is too large."
    if category not in CATEGORIES:
        return None, "Choose a valid category."
    try:
        # Re-format so the stored text is always zero-padded ISO (e.g. 2026-03-05).
        iso_date = datetime.strptime(raw_date, "%Y-%m-%d").date().isoformat()
    except ValueError:
        return None, "Enter a valid date."
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return None, f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer."

    return {
        "amount": round(amount, 2),
        "category": category,
        "date": iso_date,
        "description": description or None,
    }, None


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            form={"date": get_today().isoformat()},
        )
    if request.method != "POST":
        abort(405)

    values, error = validate_expense_form(request.form)
    if error:
        flash(error, "error")
        return render_template(
            "add_expense.html", categories=CATEGORIES, form=request.form
        )

    # user_id always comes from the session, never from the posted form.
    queries.insert_expense(
        user_id,
        values["amount"],
        values["category"],
        values["date"],
        values["description"],
    )
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Scoped to the session user, so another user's expense is simply "not found".
    expense = queries.get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        form = dict(expense, amount=f"{expense['amount']:.2f}")
        return render_template(
            "edit_expense.html", expense=expense, categories=CATEGORIES, form=form
        )
    if request.method != "POST":
        abort(405)

    values, error = validate_expense_form(request.form)
    if error:
        flash(error, "error")
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=CATEGORIES,
            form=request.form,
        )

    changed = queries.update_expense(
        id,
        user_id,
        values["amount"],
        values["category"],
        values["date"],
        values["description"],
    )
    if not changed:
        # The expense disappeared between loading the form and saving it.
        abort(404)
    flash("Expense updated.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # The DELETE is scoped to the session user, so a foreign or missing id deletes nothing.
    if not queries.delete_expense(id, user_id):
        abort(404)
    flash("Expense deleted.", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
