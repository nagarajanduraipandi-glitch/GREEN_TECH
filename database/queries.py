import math
from datetime import datetime

from database.db import get_db


def _date_filter(date_from, date_to):
    """Fixed SQL fragment plus bound values; empty unless both dates are given."""
    if date_from and date_to:
        return " AND date BETWEEN ? AND ?", (date_from, date_to)
    return "", ()


def insert_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM login_user WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    created = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created.strftime("%B %Y"),
    }


def get_summary_stats(user_id, date_from=None, date_to=None):
    clause, extra = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n "
            "FROM expenses WHERE user_id = ?" + clause,
            (user_id, *extra),
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?" + clause +
            " GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1",
            (user_id, *extra),
        ).fetchone()
    finally:
        conn.close()
    if totals["n"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
    return {
        "total_spent": round(totals["total"], 2),
        "transaction_count": totals["n"],
        "top_category": top["category"],
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    clause, extra = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            (user_id, *extra, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r["id"],
            "date": r["date"],
            "description": r["description"] or "",
            "category": r["category"],
            "amount": r["amount"],
        }
        for r in rows
    ]


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, amount, category, date, description FROM expenses "
            "WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {
        "id": row["id"],
        "amount": row["amount"],
        "category": row["category"],
        "date": row["date"],
        "description": row["description"] or "",
    }


def update_expense(expense_id, user_id, amount, category, date, description):
    """Update one of the user's expenses; returns the number of rows changed."""
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_expense(expense_id, user_id):
    """Delete one of the user's expenses; returns the number of rows deleted."""
    conn = get_db()
    try:
        cur = conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    clause, extra = _date_filter(date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY total DESC, category ASC",
            (user_id, *extra),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return []
    grand_total = sum(r["total"] for r in rows)
    items = [
        {
            "name": r["category"],
            "amount": round(r["total"], 2),
            "pct": math.floor(r["total"] / grand_total * 100 + 0.5),
        }
        for r in rows
    ]
    # Rounding can leave the percentages off 100; the largest category absorbs it.
    items[0]["pct"] += 100 - sum(i["pct"] for i in items)
    return items
