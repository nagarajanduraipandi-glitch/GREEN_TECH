import os
import re
import sqlite3
import sys
import tempfile
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as dbmod

# Throwaway database, set before the app is imported so spendly.db is never opened.
_TMP_DIR = tempfile.mkdtemp()
dbmod.DB_PATH = os.path.join(_TMP_DIR, "test_add_expense.db")

import app as appmod  # noqa: E402
from database import queries  # noqa: E402

TODAY = date(2026, 11, 15)
CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    if os.path.exists(dbmod.DB_PATH):
        os.remove(dbmod.DB_PATH)
    dbmod.init_db()
    monkeypatch.setattr(appmod, "get_today", lambda: TODAY)
    yield


@pytest.fixture
def uid():
    return dbmod.create_user("Add User", "add@example.com", "password123")


@pytest.fixture
def client(uid):
    c = appmod.app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = uid
    return c


def valid(**over):
    data = dict(amount="50.0", category="Food", date="2026-11-10", description="Lunch")
    data.update(over)
    return data


def expense_rows(user_id=None):
    conn = sqlite3.connect(dbmod.DB_PATH)
    conn.row_factory = sqlite3.Row
    sql, args = "SELECT * FROM expenses", ()
    if user_id is not None:
        sql, args = sql + " WHERE user_id = ?", (user_id,)
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------- unit tests

def test_insert_expense_with_description(uid):
    new_id = queries.insert_expense(uid, 50.0, "Food", "2026-03-20", "Lunch")
    row = expense_rows(uid)[0]
    assert row["id"] == new_id
    assert (row["amount"], row["category"], row["date"], row["description"]) == (
        50.0, "Food", "2026-03-20", "Lunch")


def test_insert_expense_without_description_stores_null(uid):
    queries.insert_expense(uid, 50.0, "Food", "2026-03-20", None)
    assert expense_rows(uid)[0]["description"] is None


def test_insert_expense_unknown_user_raises():
    with pytest.raises(sqlite3.IntegrityError):
        queries.insert_expense(999, 5.0, "Food", "2026-03-20", None)
    assert expense_rows() == []


def test_insert_expense_invalid_category_raises(uid):
    with pytest.raises(sqlite3.IntegrityError):
        queries.insert_expense(uid, 5.0, "Travel", "2026-03-20", None)


# ---------------------------------------------------------------- auth + GET

def test_get_unauthenticated_redirects():
    r = appmod.app.test_client().get("/expenses/add")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_post_unauthenticated_redirects_and_inserts_nothing(uid):
    r = appmod.app.test_client().post("/expenses/add", data=valid())
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert expense_rows() == []


def test_get_authenticated_renders_form(client):
    r = client.get("/expenses/add")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert re.search(r'<form method="post" action="/expenses/add"', body)
    options = re.findall(r'<option value="([^"]+)"', body)
    assert options == CATEGORIES
    for name in ("amount", "category", "date", "description"):
        assert f'name="{name}"' in body
    assert 'value="2026-11-15"' in body  # server-supplied default date
    assert "Amount (₹)" in body and "Save Expense" in body
    assert 'href="/profile"' in body.split("Save Expense")[1]
    assert "$" not in body and "£" not in body


# ----------------------------------------------------------------- POST valid

def test_valid_post_redirects_and_saves(client, uid):
    r = client.post("/expenses/add", data=valid())
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile")
    rows = expense_rows(uid)
    assert len(rows) == 1
    assert (rows[0]["amount"], rows[0]["category"], rows[0]["date"], rows[0]["description"]) == (
        50.0, "Food", "2026-11-10", "Lunch")


def test_new_expense_appears_on_profile(client):
    client.post("/expenses/add", data=valid(description="Visible lunch"))
    body = client.get("/profile").get_data(as_text=True)
    assert "Visible lunch" in body and "₹50.00" in body
    assert "Expense added." in body


def test_no_description_saves_null(client, uid):
    r = client.post("/expenses/add", data=valid(description=""))
    assert r.status_code == 302
    assert expense_rows(uid)[0]["description"] is None


def test_whitespace_description_saves_null(client, uid):
    client.post("/expenses/add", data=valid(description="   "))
    assert expense_rows(uid)[0]["description"] is None


def test_description_is_stripped(client, uid):
    client.post("/expenses/add", data=valid(description="  padded  "))
    assert expense_rows(uid)[0]["description"] == "padded"


def test_date_is_stored_as_zero_padded_iso(client, uid):
    r = client.post("/expenses/add", data=valid(date="2026-3-5"))
    assert r.status_code == 302
    assert expense_rows(uid)[0]["date"] == "2026-03-05"


def test_amount_rounded_to_two_decimals(client, uid):
    client.post("/expenses/add", data=valid(amount="12.3456"))
    assert expense_rows(uid)[0]["amount"] == 12.35


def test_posted_user_id_is_ignored(client, uid):
    other = dbmod.create_user("Other", "other@example.com", "password123")
    client.post("/expenses/add", data=valid(user_id=str(other)))
    assert len(expense_rows(uid)) == 1 and expense_rows(other) == []


def test_each_category_is_accepted(client, uid):
    for c in CATEGORIES:
        assert client.post("/expenses/add", data=valid(category=c)).status_code == 302
    assert len(expense_rows(uid)) == 7


def test_maximum_description_length_accepted(client, uid):
    assert client.post("/expenses/add", data=valid(description="x" * 200)).status_code == 302
    assert len(expense_rows(uid)[0]["description"]) == 200


# --------------------------------------------------------------- POST invalid

@pytest.mark.parametrize("over, message", [
    (dict(amount=""), "Amount is required."),
    (dict(amount="0"), "Enter a valid amount greater than 0."),
    (dict(amount="-5"), "Enter a valid amount greater than 0."),
    (dict(amount="abc"), "Enter a valid amount greater than 0."),
    (dict(amount="nan"), "Enter a valid amount greater than 0."),
    (dict(amount="inf"), "Enter a valid amount greater than 0."),
    (dict(amount="1e999"), "Enter a valid amount greater than 0."),
    (dict(amount="10000000.01"), "Amount is too large."),
    (dict(category="Travel"), "Choose a valid category."),
    (dict(category=""), "Choose a valid category."),
    (dict(date="not-a-date"), "Enter a valid date."),
    (dict(date=""), "Enter a valid date."),
    (dict(date="2026-02-30"), "Enter a valid date."),
    (dict(date="15/11/2026"), "Enter a valid date."),
    (dict(description="x" * 201), "Description must be 200 characters or fewer."),
])
def test_invalid_input_rerenders_with_message(client, over, message):
    r = client.post("/expenses/add", data=valid(**over))
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert message in body
    assert expense_rows() == []


def test_missing_amount_field_entirely(client):
    data = valid()
    del data["amount"]
    r = client.post("/expenses/add", data=data)
    assert r.status_code == 200 and "Amount is required." in r.get_data(as_text=True)


def test_error_keeps_submitted_values(client):
    r = client.post("/expenses/add", data=valid(
        amount="0", category="Bills", date="2026-09-09", description="Keep me"))
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'value="0"' in body
    assert re.search(r'<option value="Bills" selected>', body)
    assert 'value="2026-09-09"' in body and 'value="Keep me"' in body


# --------------------------------------------------------------------- UI

def test_profile_has_add_expense_button(client):
    body = client.get("/profile").get_data(as_text=True)
    assert re.search(r'<a href="/expenses/add" class="btn-add">Add Expense</a>', body)


def test_navbar_link_only_when_logged_in(client):
    nav = client.get("/profile").get_data(as_text=True).split("</nav>")[0]
    assert 'href="/expenses/add"' in nav
    guest = appmod.app.test_client().get("/").get_data(as_text=True).split("</nav>")[0]
    assert "/expenses/add" not in guest


def test_template_has_no_inline_styles_or_hex():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tpl = open(os.path.join(root, "templates", "add_expense.html"), encoding="utf-8").read()
    assert "style=" not in tpl
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", tpl)
    assert not re.search(r'(href|action)="/', tpl)
