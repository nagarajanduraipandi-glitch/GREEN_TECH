import os
import re
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as dbmod

# Point every connection at a throwaway database before the app is imported,
# so these tests never open spendly.db.
_TMP_DIR = tempfile.mkdtemp()
dbmod.DB_PATH = os.path.join(_TMP_DIR, "test_spendly.db")

from app import app  # noqa: E402
from database import queries  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    if os.path.exists(dbmod.DB_PATH):
        os.remove(dbmod.DB_PATH)
    dbmod.init_db()
    dbmod.seed_db()
    yield


@pytest.fixture
def client():
    return app.test_client()


def add_user(name="Empty User", email="empty@example.com"):
    return dbmod.create_user(name, email, "password123")


def add_expense(user_id, amount, category, date, description="x"):
    conn = dbmod.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    conn.close()


def login_as(client, user_id):
    with client.session_transaction() as s:
        s["user_id"] = user_id


# ---------------------------------------------------------------- unit tests

def test_get_user_by_id_valid():
    u = queries.get_user_by_id(1)
    assert u["name"] == "Demo User" and u["email"] == "demo@spendly.com"
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", u["member_since"])


def test_get_user_by_id_missing():
    assert queries.get_user_by_id(999) is None


def test_member_since_derived_from_created_at():
    conn = dbmod.get_db()
    conn.execute("UPDATE login_user SET created_at = '2026-01-15 10:00:00' WHERE id = 1")
    conn.commit()
    conn.close()
    assert queries.get_user_by_id(1)["member_since"] == "January 2026"


def test_summary_stats_with_expenses():
    s = queries.get_summary_stats(1)
    assert s == {"total_spent": 346.24, "transaction_count": 8, "top_category": "Bills"}


def test_summary_stats_no_expenses():
    uid = add_user()
    assert queries.get_summary_stats(uid) == {
        "total_spent": 0, "transaction_count": 0, "top_category": "—",
    }


def test_summary_stats_tie_breaks_alphabetically():
    uid = add_user()
    add_expense(uid, 10.0, "Health", "2026-01-01")
    add_expense(uid, 10.0, "Food", "2026-01-02")
    assert queries.get_summary_stats(uid)["top_category"] == "Food"


def test_money_is_rounded_to_two_decimals():
    uid = add_user()
    for _ in range(3):
        add_expense(uid, 0.1, "Food", "2026-01-01")
    assert queries.get_summary_stats(uid)["total_spent"] == 0.3
    assert queries.get_category_breakdown(uid)[0]["amount"] == 0.3


def test_recent_transactions_newest_first():
    t = queries.get_recent_transactions(1)
    assert len(t) == 8
    assert [x["date"] for x in t] == sorted((x["date"] for x in t), reverse=True)
    assert set(t[0]) == {"id", "date", "description", "category", "amount"}


def test_recent_transactions_same_date_by_id_desc():
    uid = add_user()
    add_expense(uid, 1.0, "Food", "2026-02-01", "first")
    add_expense(uid, 2.0, "Food", "2026-02-01", "second")
    assert [x["description"] for x in queries.get_recent_transactions(uid)] == ["second", "first"]


def test_recent_transactions_limit():
    assert len(queries.get_recent_transactions(1, limit=3)) == 3


def test_recent_transactions_empty():
    assert queries.get_recent_transactions(add_user()) == []


def test_category_breakdown_order_and_pct():
    b = queries.get_category_breakdown(1)
    assert len(b) == 7 and b[0]["name"] == "Bills"
    amounts = [x["amount"] for x in b]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(x["pct"], int) for x in b)
    assert sum(x["pct"] for x in b) == 100


def test_category_breakdown_remainder_goes_to_largest():
    uid = add_user()
    for cat in ("Food", "Bills", "Health"):  # three equal thirds: 33 + 33 + 33 = 99
        add_expense(uid, 10.0, cat, "2026-01-01")
    b = queries.get_category_breakdown(uid)
    assert sum(x["pct"] for x in b) == 100
    assert b[0]["name"] == "Bills" and b[0]["pct"] == 34


def test_category_breakdown_empty():
    assert queries.get_category_breakdown(add_user()) == []


# --------------------------------------------------------------- route tests

def test_profile_requires_login(client):
    r = client.get("/profile")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")


def test_profile_for_seed_user(client):
    login_as(client, 1)
    r = client.get("/profile")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "Demo User" in body and "demo@spendly.com" in body
    assert "₹346.24" in body
    assert re.search(r'stat-value">8<', body)
    assert re.search(r'stat-value">Bills<', body)
    assert "$" not in body and "£" not in body

    tbody = body.split("<tbody>")[1].split("</tbody>")[0]
    dates = re.findall(r"<td>(\d{4}-\d{2}-\d{2})</td>", tbody)
    assert len(dates) == 8 and dates == sorted(dates, reverse=True)

    names = re.findall(r'breakdown-name">([^<]+)<', body)
    assert sorted(names) == sorted(
        ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
    )
    pcts = [int(p) for p in re.findall(r'breakdown-percent">(\d+)%<', body)]
    assert sum(pcts) == 100


def test_profile_for_new_registered_user(client):
    client.post("/register", data=dict(
        name="New Person", email="new@example.com",
        password="password123", confirm_password="password123"))
    client.post("/login", data={"email": "new@example.com", "password": "password123"})
    r = client.get("/profile")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "New Person" in body and "NP" in body
    assert "₹0.00" in body
    assert re.search(r'stat-value">0<', body)
    assert "breakdown-row" not in body
    assert "<tbody>" not in body
    assert "Demo User" not in body.split("</nav>")[1]


def test_profile_only_shows_own_expenses(client):
    uid = add_user()
    add_expense(uid, 5.0, "Other", "2026-03-01", "private")
    login_as(client, 1)
    assert "private" not in client.get("/profile").get_data(as_text=True)


def test_profile_with_stale_session_redirects(client):
    login_as(client, 999)
    r = client.get("/profile")
    assert r.status_code == 302 and r.headers["Location"].endswith("/login")
    with client.session_transaction() as s:
        assert "user_id" not in s


def test_tests_do_not_use_real_database():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.abspath(dbmod.DB_PATH) != os.path.join(root, "spendly.db")
    assert os.path.abspath(dbmod.DB_PATH).startswith(os.path.abspath(tempfile.gettempdir()))
