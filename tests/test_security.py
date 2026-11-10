import os
import re
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as dbmod

# Throwaway database, set before the app is imported so spendly.db is never opened.
_TMP_DIR = tempfile.mkdtemp()
dbmod.DB_PATH = os.path.join(_TMP_DIR, "test_security.db")

import app as appmod  # noqa: E402
from database import queries  # noqa: E402

APP_SOURCE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py"
)

GENERIC_LOGIN_ERROR = b"Invalid email or password."


@pytest.fixture(autouse=True)
def fresh_db():
    if os.path.exists(dbmod.DB_PATH):
        os.remove(dbmod.DB_PATH)
    dbmod.init_db()
    yield


@pytest.fixture
def user_a():
    return dbmod.create_user("Alice A", "alice@example.com", "password123")


@pytest.fixture
def user_b():
    return dbmod.create_user("Bob B", "bob@example.com", "password123")


def login_as(user_id):
    """Return a fresh test client whose session belongs to user_id."""
    c = appmod.app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = user_id
    return c


@pytest.fixture
def client_a(user_a):
    return login_as(user_a)


@pytest.fixture
def anon():
    return appmod.app.test_client()


def db_rows(sql, params=()):
    conn = sqlite3.connect(dbmod.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def expense_row(expense_id):
    rows = db_rows("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    return dict(rows[0]) if rows else None


def expense_count():
    return db_rows("SELECT COUNT(*) AS n FROM expenses")[0]["n"]


def assert_tables_intact():
    names = {r["name"] for r in db_rows("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "expenses"} <= names, f"Core tables missing: {names}"


def valid(**over):
    data = dict(amount="12.50", category="Food", date="2026-11-10", description="Lunch")
    data.update(over)
    return data


def is_login_redirect(resp):
    return resp.status_code == 302 and "/login" in resp.headers["Location"]


# ------------------------------------------------ (1) unauthenticated access

class TestAuthGuard:
    def test_profile_unauthenticated_redirects_to_login(self, anon):
        resp = anon.get("/profile")
        assert is_login_redirect(resp), f"Got {resp.status_code} {resp.headers.get('Location')}"

    def test_add_expense_get_unauthenticated_redirects_to_login(self, anon):
        assert is_login_redirect(anon.get("/expenses/add"))

    def test_add_expense_post_unauthenticated_redirects_and_creates_nothing(self, anon):
        resp = anon.post("/expenses/add", data=valid())
        assert is_login_redirect(resp)
        assert expense_count() == 0, "Anonymous POST must not create an expense"

    def test_edit_expense_get_unauthenticated_redirects_to_login(self, anon, user_a):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "x")
        assert is_login_redirect(anon.get(f"/expenses/{eid}/edit"))

    def test_edit_expense_post_unauthenticated_redirects_and_unchanged(self, anon, user_a):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "orig")
        resp = anon.post(f"/expenses/{eid}/edit", data=valid(amount="99", description="hacked"))
        assert is_login_redirect(resp)
        row = expense_row(eid)
        assert row["amount"] == 10.0 and row["description"] == "orig"

    def test_delete_expense_unauthenticated_redirects_and_keeps_row(self, anon, user_a):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "x")
        resp = anon.post(f"/expenses/{eid}/delete")
        assert is_login_redirect(resp)
        assert expense_row(eid) is not None, "Anonymous delete must not remove the row"


# -------------------------------------- (2) cross-user access (IDOR) -> 404

class TestCrossUserAccess:
    @pytest.fixture
    def b_expense(self, user_b):
        return queries.insert_expense(user_b, 77.0, "Bills", "2026-11-05", "Bob private")

    def test_user_a_cannot_view_user_b_edit_page(self, client_a, b_expense):
        resp = client_a.get(f"/expenses/{b_expense}/edit")
        assert resp.status_code == 404
        assert b"Bob private" not in resp.data

    def test_user_a_cannot_edit_user_b_expense(self, client_a, b_expense):
        resp = client_a.post(
            f"/expenses/{b_expense}/edit",
            data=valid(amount="1.00", category="Other", description="pwned"),
        )
        assert resp.status_code == 404
        row = expense_row(b_expense)
        assert row["amount"] == 77.0
        assert row["category"] == "Bills"
        assert row["description"] == "Bob private"

    def test_user_a_cannot_delete_user_b_expense(self, client_a, b_expense):
        resp = client_a.post(f"/expenses/{b_expense}/delete")
        assert resp.status_code == 404
        assert expense_row(b_expense) is not None, "B's expense must survive A's delete"

    def test_profile_does_not_show_other_users_expenses(self, client_a, b_expense):
        resp = client_a.get("/profile")
        assert resp.status_code == 200
        assert b"Bob private" not in resp.data

    def test_nonexistent_expense_returns_404(self, client_a):
        assert client_a.get("/expenses/99999/edit").status_code == 404
        assert client_a.post("/expenses/99999/delete").status_code == 404


# ------------------------------------------ (3) posted user_id is ignored

class TestPostedUserIdIgnored:
    def test_add_expense_ignores_posted_user_id(self, client_a, user_a, user_b):
        resp = client_a.post("/expenses/add", data=valid(user_id=str(user_b)))
        assert resp.status_code == 302
        rows = db_rows("SELECT user_id FROM expenses")
        assert len(rows) == 1
        assert rows[0]["user_id"] == user_a, "Expense must belong to the session user"

    def test_edit_expense_ignores_posted_user_id(self, client_a, user_a, user_b):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "mine")
        resp = client_a.post(f"/expenses/{eid}/edit", data=valid(user_id=str(user_b)))
        assert resp.status_code == 302
        row = expense_row(eid)
        assert row["user_id"] == user_a
        assert row["amount"] == 12.5

    def test_edit_cannot_hijack_other_users_expense_via_user_id(self, client_a, user_a, user_b):
        eid = queries.insert_expense(user_b, 10.0, "Food", "2026-11-01", "bobs")
        resp = client_a.post(f"/expenses/{eid}/edit", data=valid(user_id=str(user_b)))
        assert resp.status_code == 404
        assert expense_row(eid)["description"] == "bobs"


# ------------------------------------------------- (4) SQL injection style

SQLI = ["' OR '1'='1", "'; DROP TABLE expenses; --", "\" OR 1=1 --", "1; DROP TABLE users;--"]


class TestSqlInjection:
    @pytest.mark.parametrize("payload", SQLI)
    def test_login_email_injection_is_rejected_safely(self, anon, user_a, payload):
        resp = anon.post("/login", data={"email": payload, "password": "password123"})
        assert resp.status_code == 200
        assert GENERIC_LOGIN_ERROR in resp.data
        with anon.session_transaction() as s:
            assert "user_id" not in s
        assert_tables_intact()

    @pytest.mark.parametrize("payload", SQLI)
    def test_login_password_injection_is_rejected_safely(self, anon, user_a, payload):
        resp = anon.post("/login", data={"email": "alice@example.com", "password": payload})
        assert resp.status_code == 200
        with anon.session_transaction() as s:
            assert "user_id" not in s
        assert_tables_intact()

    @pytest.mark.parametrize("payload", SQLI)
    def test_add_expense_category_injection_is_rejected(self, client_a, payload):
        resp = client_a.post("/expenses/add", data=valid(category=payload))
        assert resp.status_code < 500, f"Server error: {resp.status_code}"
        assert expense_count() == 0
        assert_tables_intact()

    @pytest.mark.parametrize("payload", SQLI)
    def test_edit_expense_category_injection_is_rejected(self, client_a, user_a, payload):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "x")
        resp = client_a.post(f"/expenses/{eid}/edit", data=valid(category=payload))
        assert resp.status_code < 500
        assert expense_row(eid)["category"] == "Food"
        assert_tables_intact()

    @pytest.mark.parametrize("payload", SQLI)
    def test_profile_date_filter_injection_does_not_error(self, client_a, user_a, payload):
        queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "visible")
        for params in (
            {"date_from": payload, "date_to": "2026-12-31"},
            {"date_from": "2026-01-01", "date_to": payload},
            {"date_from": payload, "date_to": payload},
        ):
            resp = client_a.get("/profile", query_string=params)
            assert resp.status_code == 200, f"{params} -> {resp.status_code}"
        assert_tables_intact()
        assert expense_count() == 1

    @pytest.mark.parametrize("payload", SQLI)
    def test_profile_category_param_injection_does_not_error(self, client_a, user_a, payload):
        resp = client_a.get("/profile", query_string={"category": payload})
        assert resp.status_code == 200
        assert_tables_intact()

    def test_injection_in_description_is_stored_literally(self, client_a, user_a):
        payload = "'); DROP TABLE expenses; --"
        resp = client_a.post("/expenses/add", data=valid(description=payload))
        assert resp.status_code == 302
        assert_tables_intact()
        assert db_rows("SELECT description FROM expenses")[0]["description"] == payload


# ------------------------------------------------------------- (5) XSS

class TestXss:
    PAYLOAD = "<script>alert(1)</script>"

    def test_description_is_escaped_on_profile(self, client_a, user_a):
        queries.insert_expense(user_a, 5.0, "Food", "2026-11-01", self.PAYLOAD)
        resp = client_a.get("/profile")
        assert resp.status_code == 200
        assert self.PAYLOAD.encode() not in resp.data, "Raw <script> tag must not be rendered"
        assert b"&lt;script&gt;" in resp.data, "Description should appear HTML-escaped"

    def test_description_posted_via_form_is_escaped_on_profile(self, client_a):
        client_a.post("/expenses/add", data=valid(description=self.PAYLOAD))
        resp = client_a.get("/profile")
        assert self.PAYLOAD.encode() not in resp.data
        assert b"&lt;script&gt;" in resp.data

    def test_description_is_escaped_on_edit_page(self, client_a, user_a):
        eid = queries.insert_expense(user_a, 5.0, "Food", "2026-11-01", self.PAYLOAD)
        resp = client_a.get(f"/expenses/{eid}/edit")
        assert resp.status_code == 200
        assert self.PAYLOAD.encode() not in resp.data

    def test_user_name_is_escaped_on_profile(self):
        uid = dbmod.create_user("<script>alert(2)</script>", "xss@example.com", "password123")
        resp = login_as(uid).get("/profile")
        assert resp.status_code == 200
        assert b"<script>alert(2)</script>" not in resp.data

    def test_login_email_is_escaped_when_redisplayed(self, anon):
        resp = anon.post("/login", data={"email": '"><script>alert(3)</script>', "password": "x"})
        assert resp.status_code == 200
        assert b"<script>alert(3)</script>" not in resp.data


# ----------------------------------------------------- (6) invalid amounts

class TestInvalidAmounts:
    BAD = ["nan", "NaN", "inf", "-inf", "Infinity", "-5", "-0.01", "0", "abc", "",
           "1e308", "1e12", "99999999999999999999"]

    @pytest.mark.parametrize("amount", BAD)
    def test_add_expense_rejects_invalid_amount(self, client_a, amount):
        resp = client_a.post("/expenses/add", data=valid(amount=amount))
        assert resp.status_code == 200, "Invalid input should re-render the form"
        assert expense_count() == 0, f"Amount {amount!r} must not be stored"

    @pytest.mark.parametrize("amount", BAD)
    def test_edit_expense_rejects_invalid_amount(self, client_a, user_a, amount):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "orig")
        resp = client_a.post(f"/expenses/{eid}/edit", data=valid(amount=amount))
        assert resp.status_code == 200
        assert expense_row(eid)["amount"] == 10.0, f"Amount {amount!r} must not be saved"

    def test_add_expense_missing_amount_field_rejected(self, client_a):
        data = valid()
        del data["amount"]
        resp = client_a.post("/expenses/add", data=data)
        assert resp.status_code == 200
        assert expense_count() == 0


# ------------------------------------------------------- (7) session handling

class TestSessionHandling:
    def test_logout_clears_session(self, client_a):
        client_a.get("/logout")
        with client_a.session_transaction() as s:
            assert "user_id" not in s, "Session must be cleared on logout"

    def test_protected_route_inaccessible_after_logout(self, client_a):
        client_a.get("/logout")
        assert is_login_redirect(client_a.get("/profile"))

    def test_forged_unknown_user_id_is_redirected_and_cleared(self):
        c = login_as(987654)
        resp = c.get("/profile")
        assert is_login_redirect(resp)
        with c.session_transaction() as s:
            assert "user_id" not in s, "Forged session must be cleared"

    def test_forged_user_id_cannot_create_expense(self):
        c = login_as(987654)
        resp = c.post("/expenses/add", data=valid())
        assert resp.status_code < 500, "Unknown user must not cause a server error"
        assert expense_count() == 0, "No expense may be created for a nonexistent user"

    def test_successful_login_sets_session_user(self, anon, user_a):
        resp = anon.post("/login", data={"email": "alice@example.com", "password": "password123"})
        assert resp.status_code == 302
        with anon.session_transaction() as s:
            assert s.get("user_id") == user_a


# ---------------------------------------- (8) generic login error (no enumeration)

class TestLoginErrorGeneric:
    def test_unknown_email_and_wrong_password_same_error(self, anon, user_a):
        r_unknown = anon.post("/login", data={"email": "nobody@example.com", "password": "password123"})
        r_wrong = anon.post("/login", data={"email": "alice@example.com", "password": "wrongpass99"})
        assert r_unknown.status_code == r_wrong.status_code == 200
        assert GENERIC_LOGIN_ERROR in r_unknown.data
        assert GENERIC_LOGIN_ERROR in r_wrong.data

    def test_error_messages_do_not_reveal_which_field_failed(self, anon, user_a):
        r_unknown = anon.post("/login", data={"email": "nobody@example.com", "password": "password123"})
        r_wrong = anon.post("/login", data={"email": "alice@example.com", "password": "wrongpass99"})
        for r in (r_unknown, r_wrong):
            lowered = r.data.lower()
            assert b"no account" not in lowered
            assert b"not registered" not in lowered
            assert b"user not found" not in lowered
            assert b"incorrect password" not in lowered

    def test_failed_login_does_not_set_session(self, anon, user_a):
        anon.post("/login", data={"email": "alice@example.com", "password": "wrongpass99"})
        with anon.session_transaction() as s:
            assert "user_id" not in s

    def test_empty_credentials_get_generic_error(self, anon, user_a):
        resp = anon.post("/login", data={"email": "", "password": ""})
        assert resp.status_code == 200
        assert GENERIC_LOGIN_ERROR in resp.data


# --------------------------------------------- (9) CSRF  (not implemented yet)

CSRF_REASON = "CSRF protection is not implemented yet"


class TestCsrf:
    @pytest.fixture(autouse=True)
    def enable_csrf(self):
        # Make sure testing mode does not hide a CSRF check, if one is added later.
        appmod.app.config["WTF_CSRF_ENABLED"] = True
        yield
        appmod.app.config.pop("WTF_CSRF_ENABLED", None)

    @pytest.mark.xfail(strict=False, reason=CSRF_REASON)
    def test_add_expense_post_without_csrf_token_is_rejected(self, client_a):
        resp = client_a.post("/expenses/add", data=valid())
        assert resp.status_code in (400, 403), f"Got {resp.status_code}"
        assert expense_count() == 0

    @pytest.mark.xfail(strict=False, reason=CSRF_REASON)
    def test_edit_expense_post_without_csrf_token_is_rejected(self, client_a, user_a):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "orig")
        resp = client_a.post(f"/expenses/{eid}/edit", data=valid(amount="99"))
        assert resp.status_code in (400, 403), f"Got {resp.status_code}"
        assert expense_row(eid)["amount"] == 10.0

    @pytest.mark.xfail(strict=False, reason=CSRF_REASON)
    def test_delete_expense_post_without_csrf_token_is_rejected(self, client_a, user_a):
        eid = queries.insert_expense(user_a, 10.0, "Food", "2026-11-01", "orig")
        resp = client_a.post(f"/expenses/{eid}/delete")
        assert resp.status_code in (400, 403), f"Got {resp.status_code}"
        assert expense_row(eid) is not None

    @pytest.mark.xfail(strict=False, reason=CSRF_REASON)
    def test_add_expense_post_with_invalid_csrf_token_is_rejected(self, client_a):
        resp = client_a.post("/expenses/add", data=valid(csrf_token="forged-token"))
        assert resp.status_code in (400, 403), f"Got {resp.status_code}"
        assert expense_count() == 0

    @pytest.mark.xfail(strict=False, reason=CSRF_REASON)
    def test_login_post_without_csrf_token_is_rejected(self, anon, user_a):
        resp = anon.post("/login", data={"email": "alice@example.com", "password": "password123"})
        assert resp.status_code in (400, 403), f"Got {resp.status_code}"

    def test_session_cookie_has_samesite_set(self):
        assert appmod.app.config.get("SESSION_COOKIE_SAMESITE") in ("Lax", "Strict")


# ------------------------------------------------ (10) logout via GET

class TestLogoutMethod:
    @pytest.mark.xfail(strict=False, reason="/logout currently logs out on GET (CSRF-able); should require POST")
    def test_logout_via_get_does_not_log_out(self, client_a, user_a):
        client_a.get("/logout")
        with client_a.session_transaction() as s:
            assert s.get("user_id") == user_a, "GET /logout must not end the session"

    @pytest.mark.xfail(strict=False, reason="/logout currently accepts GET; should only allow POST")
    def test_logout_get_returns_405(self, client_a):
        assert client_a.get("/logout").status_code == 405


# --------------------------------------------- (11) configuration hygiene

class TestConfiguration:
    @staticmethod
    def _source():
        with open(APP_SOURCE_PATH, encoding="utf-8") as f:
            return f.read()

    @pytest.mark.xfail(strict=False, reason="app.run(debug=True) is hard-coded in app.py")
    def test_app_does_not_hardcode_debug_true(self):
        assert not re.search(r"debug\s*=\s*True", self._source()), \
            "debug=True must not be hard-coded (Werkzeug debugger allows remote code execution)"

    @pytest.mark.xfail(strict=False, reason="Known fallback SECRET_KEY 'dev-secret-change-me' is still used")
    def test_app_does_not_use_known_fallback_secret_key(self):
        assert "dev-secret-change-me" not in self._source(), \
            "A publicly known fallback secret lets attackers forge session cookies"

    def test_app_debug_flag_is_off_under_test(self):
        assert appmod.app.debug is False

    def test_secret_key_is_configured(self):
        assert appmod.app.secret_key, "SECRET_KEY must not be empty"

    def test_session_cookie_is_httponly(self):
        assert appmod.app.config.get("SESSION_COOKIE_HTTPONLY", True) is True
