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
dbmod.DB_PATH = os.path.join(_TMP_DIR, "test_delete_expense.db")

import app as appmod  # noqa: E402
from database import queries  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    if os.path.exists(dbmod.DB_PATH):
        os.remove(dbmod.DB_PATH)
    dbmod.init_db()
    monkeypatch.setattr(appmod, "get_today", lambda: date(2026, 11, 15))
    yield


@pytest.fixture
def uid():
    return dbmod.create_user("Delete User", "delete@example.com", "password123")


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


def exists(expense_id):
    conn = sqlite3.connect(dbmod.DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM expenses WHERE id = ?", (expense_id,)).fetchone()[0]
    conn.close()
    return n == 1


def total_rows():
    conn = sqlite3.connect(dbmod.DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    return n


def url(expense_id):
    return f"/expenses/{expense_id}/delete"


# ---------------------------------------------------------------- unit tests

def test_delete_own_expense(uid, eid):
    assert queries.delete_expense(eid, uid) == 1
    assert not exists(eid)


def test_delete_wrong_user_keeps_row(eid, other):
    assert queries.delete_expense(eid, other) == 0
    assert exists(eid)


def test_delete_missing_id_changes_nothing(uid, eid):
    assert queries.delete_expense(999, uid) == 0
    assert total_rows() == 1


def test_delete_only_removes_target(uid, eid):
    keep = queries.insert_expense(uid, 1.0, "Other", "2026-11-01", "keep")
    queries.delete_expense(eid, uid)
    assert exists(keep) and not exists(eid)


def test_helper_is_not_shadowed_by_the_view():
    assert queries.delete_expense is not appmod.delete_expense
    assert appmod.app.view_functions["delete_expense"] is appmod.delete_expense


# ------------------------------------------------------------------- routes

def test_post_unauthenticated_redirects_and_deletes_nothing(eid):
    r = appmod.app.test_client().post(url(eid))
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    assert exists(eid)


def test_post_own_expense_deletes_and_redirects(client, eid):
    r = client.post(url(eid))
    assert r.status_code == 302 and r.headers["Location"].endswith("/profile")
    assert not exists(eid)


def test_deleted_expense_gone_from_profile_with_message(client, uid, eid):
    keep = queries.insert_expense(uid, 7.0, "Bills", "2026-11-11", "Stays")
    client.post(url(eid))
    body = client.get("/profile").get_data(as_text=True)
    assert "Expense deleted." in body
    assert "Lunch" not in body and "Stays" in body
    assert "₹7.00" in body and exists(keep)


def test_post_other_users_expense_is_404(client, other):
    foreign = queries.insert_expense(other, 7.0, "Other", "2026-11-01", "theirs")
    assert client.post(url(foreign)).status_code == 404
    assert exists(foreign)


def test_post_missing_id_is_404(client):
    assert client.post(url(999)).status_code == 404


def test_deleting_twice_gives_404_the_second_time(client, eid):
    assert client.post(url(eid)).status_code == 302
    assert client.post(url(eid)).status_code == 404


def test_non_integer_id_is_404(client):
    assert client.post("/expenses/abc/delete").status_code == 404


# ------------------------------------------------------------------ methods

def test_get_returns_405_for_every_caller(client, eid):
    assert client.get(url(eid)).status_code == 405
    assert client.get(url(999)).status_code == 405
    assert appmod.app.test_client().get(url(eid)).status_code == 405
    assert exists(eid)


@pytest.mark.parametrize("method", ["put", "delete", "patch"])
def test_other_methods_return_405(client, eid, method):
    assert getattr(client, method)(url(eid)).status_code == 405
    assert exists(eid)


# ----------------------------------------------------------------------- UI

def test_each_row_has_edit_link_and_delete_form(client, uid):
    ids = [queries.insert_expense(uid, float(i + 1), "Food", f"2026-11-{i + 1:02d}", f"row{i}")
           for i in range(3)]
    body = client.get("/profile").get_data(as_text=True)
    forms = re.findall(
        r'<form method="post" action="(/expenses/\d+/delete)" class="inline-form" '
        r'data-confirm="Delete this expense\?">\s*<button type="submit" class="btn-delete">Delete</button>',
        body)
    assert sorted(forms) == sorted(url(i) for i in ids)
    edits = re.findall(r'<a href="(/expenses/\d+/edit)" class="row-action">Edit</a>', body)
    assert len(edits) == 3


def test_profile_template_has_no_inline_handlers_or_styles():
    tpl = open(os.path.join(ROOT, "templates", "profile.html"), encoding="utf-8").read()
    assert "style=" not in tpl and "onsubmit" not in tpl and "onclick" not in tpl
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", tpl)


def test_confirm_listener_is_in_main_js():
    js = open(os.path.join(ROOT, "static", "js", "main.js"), encoding="utf-8").read()
    assert 'addEventListener("submit"' in js and "data-confirm" in js
    assert "window.confirm(message)" in js and "event.preventDefault()" in js


def test_btn_delete_uses_css_variables():
    css = open(os.path.join(ROOT, "static", "css", "style.css"), encoding="utf-8").read()
    block = css.split(".btn-delete {")[1].split("}")[0]
    assert "var(--danger)" in block and not re.search(r"#[0-9a-fA-F]{3,8}\b", block)


def test_session_cookie_is_samesite_lax(client):
    r = appmod.app.test_client().post(
        "/login", data={"email": "nobody@example.com", "password": "x"})
    c = appmod.app.test_client()
    c.post("/register", data=dict(name="Cookie User", email="cookie@example.com",
                                  password="password123", confirm_password="password123"))
    r = c.post("/login", data={"email": "cookie@example.com", "password": "password123"})
    cookie = r.headers.get("Set-Cookie", "")
    assert "SameSite=Lax" in cookie
