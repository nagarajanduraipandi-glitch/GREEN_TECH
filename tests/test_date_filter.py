import os
import re
import sys
import tempfile
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.db as dbmod

# Throwaway database, set before the app is imported so spendly.db is never opened.
_TMP_DIR = tempfile.mkdtemp()
dbmod.DB_PATH = os.path.join(_TMP_DIR, "test_date_filter.db")

import app as appmod  # noqa: E402
from database import queries  # noqa: E402

TODAY = date(2026, 11, 15)

# (date, category, amount)
EXPENSES = [
    ("2026-05-31", "Other", 5.00),
    ("2026-08-15", "Bills", 10.00),
    ("2026-09-10", "Food", 20.00),
    ("2026-11-01", "Food", 30.00),
    ("2026-11-15", "Transport", 40.00),
    ("2026-11-20", "Health", 50.00),  # after "today"
]


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    if os.path.exists(dbmod.DB_PATH):
        os.remove(dbmod.DB_PATH)
    dbmod.init_db()
    monkeypatch.setattr(appmod, "get_today", lambda: TODAY)
    yield


@pytest.fixture
def uid():
    user_id = dbmod.create_user("Filter User", "filter@example.com", "password123")
    conn = dbmod.get_db()
    for d, cat, amt in EXPENSES:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amt, cat, d, f"{cat} on {d}"),
        )
    conn.commit()
    conn.close()
    return user_id


@pytest.fixture
def client(uid):
    c = appmod.app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = uid
    return c


def page(client, query=""):
    r = client.get("/profile" + query)
    assert r.status_code == 200
    return r.get_data(as_text=True)


def stat(body, label):
    m = re.search(
        rf'stat-label">{label}</span>\s*<span class="stat-value">([^<]*)<', body
    )
    return m.group(1)


def rows(body):
    if "<tbody>" not in body:
        return []
    tbody = body.split("<tbody>")[1].split("</tbody>")[0]
    return re.findall(r"<td>(\d{4}-\d{2}-\d{2})</td>", tbody)


def active_labels(body):
    return re.findall(r'filter-btn filter-btn-active">([^<]+)<', body)


# ------------------------------------------------------------ date helpers

def test_add_months_clamps_to_month_end():
    assert appmod.add_months(date(2026, 5, 31), 3) == date(2026, 2, 28)
    assert appmod.add_months(date(2026, 3, 31), 1) == date(2026, 2, 28)
    assert appmod.add_months(date(2024, 3, 31), 1) == date(2024, 2, 29)


def test_add_months_crosses_year_boundary():
    assert appmod.add_months(date(2026, 2, 10), 3) == date(2025, 11, 10)
    assert appmod.add_months(date(2026, 1, 31), 12) == date(2025, 1, 31)


def test_parse_date():
    assert appmod.parse_date("2026-11-15") == "2026-11-15"
    for bad in (None, "", "not-a-date", "2026-13-01", "15-11-2026", "2026-02-30"):
        assert appmod.parse_date(bad) is None


def test_build_presets():
    assert appmod.build_presets(TODAY) == [
        ("This Month", "2026-11-01", "2026-11-15"),
        ("Last 3 Months", "2026-08-15", "2026-11-15"),
        ("Last 6 Months", "2026-05-15", "2026-11-15"),
    ]


# ----------------------------------------------------------- query helpers

def test_helpers_without_dates_are_unfiltered(uid):
    assert queries.get_summary_stats(uid)["transaction_count"] == 6
    assert queries.get_summary_stats(uid, None, None) == queries.get_summary_stats(uid)
    assert len(queries.get_recent_transactions(uid)) == 6
    assert len(queries.get_category_breakdown(uid)) == 5


def test_helpers_with_range_are_inclusive(uid):
    s = queries.get_summary_stats(uid, "2026-11-01", "2026-11-15")
    assert s == {"total_spent": 70.0, "transaction_count": 2, "top_category": "Transport"}
    t = queries.get_recent_transactions(uid, date_from="2026-11-01", date_to="2026-11-15")
    assert [x["date"] for x in t] == ["2026-11-15", "2026-11-01"]
    b = queries.get_category_breakdown(uid, "2026-11-01", "2026-11-15")
    assert [x["name"] for x in b] == ["Transport", "Food"]
    assert sum(x["pct"] for x in b) == 100


def test_helpers_single_day_range(uid):
    s = queries.get_summary_stats(uid, "2026-11-15", "2026-11-15")
    assert s["transaction_count"] == 1 and s["total_spent"] == 40.0


def test_helpers_empty_range(uid):
    assert queries.get_summary_stats(uid, "2020-01-01", "2020-01-31") == {
        "total_spent": 0, "transaction_count": 0, "top_category": "—",
    }
    assert queries.get_recent_transactions(uid, date_from="2020-01-01", date_to="2020-01-31") == []
    assert queries.get_category_breakdown(uid, "2020-01-01", "2020-01-31") == []


def test_helpers_use_one_sided_dates_as_unfiltered(uid):
    assert queries.get_summary_stats(uid, "2026-11-01", None)["transaction_count"] == 6


# ------------------------------------------------------------------- route

def test_no_params_is_unfiltered(client):
    body = page(client)
    assert stat(body, "Transactions") == "6"
    assert stat(body, "Total spent") == "₹155.00"
    assert len(rows(body)) == 6
    assert active_labels(body) == ["All Time"]
    assert "filter-custom-active" not in body


def test_this_month_preset(client):
    body = page(client, "?date_from=2026-11-01&date_to=2026-11-15")
    assert stat(body, "Transactions") == "2"
    assert stat(body, "Total spent") == "₹70.00"
    assert rows(body) == ["2026-11-15", "2026-11-01"]
    assert len(re.findall("breakdown-row", body)) == 2
    assert active_labels(body) == ["This Month"]
    assert "filter-custom-active" not in body


def test_last_3_and_6_month_presets(client):
    body = page(client, "?date_from=2026-08-15&date_to=2026-11-15")
    assert stat(body, "Transactions") == "4"  # 08-15, 09-10, 11-01, 11-15
    assert active_labels(body) == ["Last 3 Months"]
    body = page(client, "?date_from=2026-05-15&date_to=2026-11-15")
    assert stat(body, "Transactions") == "5"  # 05-31, 08-15, 09-10, 11-01, 11-15
    assert "2026-05-31" in body
    assert active_labels(body) == ["Last 6 Months"]


def test_preset_links_are_generated_in_the_view(client):
    body = page(client)
    links = re.findall(r'<a href="([^"]+)" class="filter-btn', body)
    assert links == [
        "/profile?date_from=2026-11-01&amp;date_to=2026-11-15",
        "/profile?date_from=2026-08-15&amp;date_to=2026-11-15",
        "/profile?date_from=2026-05-15&amp;date_to=2026-11-15",
        "/profile",
    ]


def test_all_time_removes_filter(client):
    filtered = page(client, "?date_from=2026-11-01&date_to=2026-11-15")
    assert stat(filtered, "Transactions") == "2"
    assert stat(page(client), "Transactions") == "6"


def test_custom_range(client):
    body = page(client, "?date_from=2026-09-01&date_to=2026-09-30")
    assert stat(body, "Transactions") == "1" and stat(body, "Total spent") == "₹20.00"
    assert rows(body) == ["2026-09-10"]
    assert active_labels(body) == []
    assert "filter-custom-active" in body
    assert 'value="2026-09-01"' in body and 'value="2026-09-30"' in body


def test_custom_range_equal_dates(client):
    body = page(client, "?date_from=2026-11-15&date_to=2026-11-15")
    assert stat(body, "Transactions") == "1"
    assert "Start date must be before end date." not in body


def test_reversed_range_flashes_and_falls_back(client):
    body = page(client, "?date_from=2026-11-15&date_to=2026-11-01")
    assert "Start date must be before end date." in body
    assert stat(body, "Transactions") == "6"
    assert active_labels(body) == ["All Time"]


def test_malformed_date_falls_back_silently(client):
    for q in ("?date_from=not-a-date&date_to=2026-11-15",
              "?date_from=2026-11-01&date_to=2026-13-45",
              "?date_from=&date_to=",
              "?date_from=%27%3B+DROP+TABLE+expenses%3B--&date_to=2026-11-15"):
        body = page(client, q)
        assert stat(body, "Transactions") == "6", q
        assert "Start date must be before end date." not in body, q


def test_one_sided_range_is_unfiltered(client):
    for q in ("?date_from=2026-11-01", "?date_to=2026-11-15"):
        body = page(client, q)
        assert stat(body, "Transactions") == "6", q
        assert "Start date must be before end date." not in body, q


def test_empty_range_shows_zero_state(client):
    body = page(client, "?date_from=2020-01-01&date_to=2020-01-31")
    assert stat(body, "Total spent") == "₹0.00"
    assert stat(body, "Transactions") == "0"
    assert stat(body, "Top category") == "—"
    assert rows(body) == []
    assert "breakdown-row" not in body
    assert "filter-custom-active" in body


def test_amounts_keep_rupee_symbol_when_filtered(client):
    body = page(client, "?date_from=2026-11-01&date_to=2026-11-15")
    assert body.count("₹") >= 5
    assert "$" not in body and "£" not in body


def test_custom_form_is_get_to_profile(client):
    body = page(client)
    m = re.search(r'<form method="get" action="([^"]+)" class="filter-custom', body)
    assert m and m.group(1) == "/profile"
    assert 'name="date_from"' in body and 'name="date_to"' in body


def test_no_inline_styles_or_hex_in_template_and_css():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tpl = open(os.path.join(root, "templates", "profile.html"), encoding="utf-8").read()
    css = open(os.path.join(root, "static", "css", "profile.css"), encoding="utf-8").read()
    assert "style=" not in tpl
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", tpl + css)


def test_filter_only_covers_own_expenses(client):
    other = dbmod.create_user("Other", "other@example.com", "password123")
    conn = dbmod.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) "
        "VALUES (?, 99.0, 'Food', '2026-11-10', 'not mine')",
        (other,),
    )
    conn.commit()
    conn.close()
    body = page(client, "?date_from=2026-11-01&date_to=2026-11-15")
    assert "not mine" not in body and stat(body, "Transactions") == "2"
