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
dbmod.DB_PATH = os.path.join(_TMP_DIR, "test_edit_expense.db")

import app as appmod  # noqa: E402
from database import queries  # noqa: E402

TODAY = date(2026, 11, 15)


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    if os.path.exists(dbmod.DB_PATH):
        os.remove(dbmod.DB_PATH)
    dbmod.init_db()
    monkeypatch.setattr(appmod, "get_today", lambda: TODAY)
    yield


@pytest.fixture
def uid():
    return dbmod.create_user("Edit User", "edit@example.com", "password123")


@pytest.fixture
def other():
    return dbmod.create_user("Other User", "other@example.com", "password123")


@pytest.fixture
def eid(uid):
    return queries.insert_expense(uid, 50.0, "Food", "2026-11-10", "Lunch")


@pytest.fixture
def client(uid):
    c = appmod.app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = uid
    return c


def row(expense_id):
    conn = sqlite3.connect(dbmod.DB_PATH)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    return r


def valid(**over):
    data = dict(amount="99.0", category="Bills", date="2026-11-12", description="Updated")
    data.update(over)
    return data


def url(expense_id):
    return f"/expenses/{expense_id}/edit"


# ---------------------------------------------------------------- unit tests

def test_get_expense_by_id_own(uid, eid):
    e = queries.get_expense_by_id(eid, uid)
    assert e == {"id": eid, "amount": 50.0, "category": "Food",
                 "date": "2026-11-10", "description": "Lunch"}


def test_get_expense_by_id_wrong_user(eid, other):
    assert queries.get_expense_by_id(eid, other) is None


def test_get_expense_by_id_missing(uid):
    assert queries.get_expense_by_id(999, uid) is None


def test_get_expense_by_id_null_description_is_blank(uid):
    new_id = queries.insert_expense(uid, 5.0, "Food", "2026-11-01", None)
    assert queries.get_expense_by_id(new_id, uid)["description"] == ""


def test_update_expense_changes_all_fields(uid, eid):
    n = queries.update_expense(eid, uid, 99.0, "Bills", "2026-11-12", None)
    r = row(eid)
    assert n == 1
    assert (r["amount"], r["category"], r["date"], r["description"]) == (
        99.0, "Bills", "2026-11-12", None)
    assert r["user_id"] == uid


def test_update_expense_wrong_user_changes_nothing(eid, other):
    assert queries.update_expense(eid, other, 99.0, "Bills", "2026-11-12", "x") == 0
    r = row(eid)
    assert (r["amount"], r["category"], r["description"]) == (50.0, "Food", "Lunch")


def test_update_expense_missing_id_returns_zero(uid):
    assert queries.update_expense(999, uid, 1.0, "Food", "2026-11-12", None) == 0


def test_recent_transactions_include_id(uid, eid):
    assert queries.get_recent_transactions(uid)[0]["id"] == eid


# -------------------------------------------------------- auth + not found

def test_get_unauthenticated_redirects(eid):
    r = appmod.app.test_client().get(url(eid))
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_post_unauthenticated_redirects_and_changes_nothing(eid):
    r = appmod.app.test_client().post(url(eid), data=valid())
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert row(eid)["amount"] == 50.0


def test_other_users_expense_is_404(client, other):
    foreign = queries.insert_expense(other, 7.0, "Other", "2026-11-01", "theirs")
    assert client.get(url(foreign)).status_code == 404
    assert client.post(url(foreign), data=valid()).status_code == 404
    r = row(foreign)
    assert (r["amount"], r["category"], r["description"]) == (7.0, "Other", "theirs")


def test_missing_expense_is_404(client):
    assert client.get(url(999)).status_code == 404
    assert client.post(url(999), data=valid()).status_code == 404


def test_non_integer_id_is_404(client):
    assert client.get("/expenses/abc/edit").status_code == 404


# ----------------------------------------------------------------------- GET

def test_get_prefills_form(client, eid):
    r = client.get(url(eid))
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert f'<form method="post" action="/expenses/{eid}/edit"' in body
    assert 'value="50.00"' in body and 'value="2026-11-10"' in body and 'value="Lunch"' in body
    assert re.search(r'<option value="Food" selected>', body)
    assert body.count(" selected>") == 1
    assert re.findall(r'<option value="([^"]+)"', body) == [
        "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
    assert "Save Changes" in body and "Amount (₹)" in body
    assert 'href="/profile"' in body.split("Save Changes")[1]
    assert "$" not in body and "£" not in body


def test_get_with_null_description(client, uid):
    new_id = queries.insert_expense(uid, 5.0, "Health", "2026-11-01", None)
    body = client.get(url(new_id)).get_data(as_text=True)
    assert 'name="description"' in body and "None" not in body
    assert re.search(r'<option value="Health" selected>', body)


# ---------------------------------------------------------------- POST valid

def test_valid_post_updates_and_redirects(client, uid, eid):
    r = client.post(url(eid), data=valid())
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile")
    x = row(eid)
    assert (x["amount"], x["category"], x["date"], x["description"]) == (
        99.0, "Bills", "2026-11-12", "Updated")
    assert x["user_id"] == uid


def test_updated_values_appear_on_profile(client, eid):
    client.post(url(eid), data=valid(description="Shows on profile"))
    body = client.get("/profile").get_data(as_text=True)
    assert "Shows on profile" in body and "₹99.00" in body and "Expense updated." in body
    assert "Lunch" not in body


def test_no_description_stores_null(client, eid):
    assert client.post(url(eid), data=valid(description="")).status_code == 302
    assert row(eid)["description"] is None


def test_whitespace_description_stores_null(client, eid):
    client.post(url(eid), data=valid(description="   "))
    assert row(eid)["description"] is None


def test_date_is_normalised_to_iso(client, eid):
    client.post(url(eid), data=valid(date="2026-3-5"))
    assert row(eid)["date"] == "2026-03-05"


def test_amount_is_rounded(client, eid):
    client.post(url(eid), data=valid(amount="12.3456"))
    assert row(eid)["amount"] == 12.35


def test_posted_user_id_is_ignored(client, uid, eid, other):
    client.post(url(eid), data=valid(user_id=str(other)))
    assert row(eid)["user_id"] == uid and row(eid)["amount"] == 99.0


def test_only_the_target_row_changes(client, uid, eid):
    sibling = queries.insert_expense(uid, 8.0, "Other", "2026-11-02", "keep")
    client.post(url(eid), data=valid())
    r = row(sibling)
    assert (r["amount"], r["category"], r["description"]) == (8.0, "Other", "keep")


# -------------------------------------------------------------- POST invalid

@pytest.mark.parametrize("over, message", [
    (dict(amount=""), "Amount is required."),
    (dict(amount="0"), "Enter a valid amount greater than 0."),
    (dict(amount="-5"), "Enter a valid amount greater than 0."),
    (dict(amount="abc"), "Enter a valid amount greater than 0."),
    (dict(amount="nan"), "Enter a valid amount greater than 0."),
    (dict(amount="inf"), "Enter a valid amount greater than 0."),
    (dict(amount="10000000.01"), "Amount is too large."),
    (dict(category="Travel"), "Choose a valid category."),
    (dict(date="not-a-date"), "Enter a valid date."),
    (dict(date="2026-02-30"), "Enter a valid date."),
    (dict(description="x" * 201), "Description must be 200 characters or fewer."),
])
def test_invalid_input_rerenders_and_changes_nothing(client, eid, over, message):
    r = client.post(url(eid), data=valid(**over))
    assert r.status_code == 200
    assert message in r.get_data(as_text=True)
    x = row(eid)
    assert (x["amount"], x["category"], x["date"], x["description"]) == (
        50.0, "Food", "2026-11-10", "Lunch")


def test_missing_amount_field_entirely(client, eid):
    data = valid()
    del data["amount"]
    r = client.post(url(eid), data=data)
    assert r.status_code == 200 and "Amount is required." in r.get_data(as_text=True)


def test_error_shows_submitted_not_original_values(client, eid):
    r = client.post(url(eid), data=valid(
        amount="0", category="Shopping", date="2026-09-09", description="Typed text"))
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert 'value="0"' in body and 'value="2026-09-09"' in body and 'value="Typed text"' in body
    assert re.search(r'<option value="Shopping" selected>', body)
    assert 'value="Lunch"' not in body and 'value="50.00"' not in body
    assert f'action="/expenses/{eid}/edit"' in body


def test_deleted_between_load_and_save_is_404(client, uid, eid):
    client.get(url(eid))
    conn = dbmod.get_db()
    conn.execute("DELETE FROM expenses WHERE id = ?", (eid,))
    conn.commit()
    conn.close()
    assert client.post(url(eid), data=valid()).status_code == 404


# --------------------------------------------------------------------- UI

def test_every_profile_row_has_its_own_edit_link(client, uid):
    ids = [queries.insert_expense(uid, float(i + 1), "Food", f"2026-11-{i + 1:02d}", f"row{i}")
           for i in range(3)]
    body = client.get("/profile").get_data(as_text=True)
    assert "<th>Actions</th>" in body
    links = re.findall(r'<a href="(/expenses/\d+/edit)" class="row-action">Edit</a>', body)
    assert sorted(links) == sorted(url(i) for i in ids)


def test_templates_have_no_inline_styles_hex_or_hardcoded_paths():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("edit_expense.html", "_expense_form.html", "add_expense.html"):
        tpl = open(os.path.join(root, "templates", name), encoding="utf-8").read()
        assert "style=" not in tpl, name
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", tpl), name
        assert not re.search(r'(href|action)="/', tpl), name
