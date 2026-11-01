"""Library Management System - Web interface (Flask + SQLite)
Run:  python3 web_app.py   then open  http://127.0.0.1:5000
"""
import sqlite3
import os
from datetime import date, timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from jinja2 import DictLoader

DB = "library.db"
LOAN_DAYS = 14
FINE_PER_DAY = 2

app = Flask(__name__)
app.secret_key = "library-secret"


def get_db():
    first_time = not os.path.exists(DB)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if first_time:
        with open("schema.sql") as f:
            conn.executescript(f.read())
    return conn


# ---------------- HTML TEMPLATES ----------------
BASE = """
<!doctype html>
<html><head><meta charset="utf-8"><title>Library Management System</title>
<style>
 *{box-sizing:border-box} body{margin:0;font-family:Segoe UI,Arial,sans-serif;background:#f3f5f9;color:#1f2937}
 nav{background:#1e3a8a;padding:0 30px;display:flex;align-items:center;gap:6px}
 nav .brand{color:#fff;font-weight:700;font-size:19px;margin-right:25px;padding:16px 0}
 nav a{color:#c7d2fe;text-decoration:none;padding:18px 14px;font-size:15px}
 nav a:hover,nav a.on{background:#2b4bb5;color:#fff}
 .wrap{max-width:1100px;margin:28px auto;padding:0 20px}
 h2{margin:0 0 18px;color:#1e3a8a}
 .cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:26px}
 .card{background:#fff;border-radius:10px;padding:20px;box-shadow:0 1px 4px #0001;border-top:4px solid #3b82f6}
 .card.g{border-color:#10b981}.card.o{border-color:#f59e0b}.card.r{border-color:#ef4444}
 .card .n{font-size:34px;font-weight:700}.card .l{color:#6b7280;font-size:14px}
 .box{background:#fff;border-radius:10px;padding:22px;box-shadow:0 1px 4px #0001;margin-bottom:24px}
 table{width:100%;border-collapse:collapse}
 th{background:#eef2ff;color:#1e3a8a;text-align:left;padding:10px;font-size:14px}
 td{padding:10px;border-bottom:1px solid #e5e7eb;font-size:14px}
 tr.late td{background:#fef2f2}
 input,select{padding:9px;border:1px solid #cbd5e1;border-radius:6px;font-size:14px;margin:0 8px 8px 0}
 button,.btn{background:#2563eb;color:#fff;border:0;padding:9px 18px;border-radius:6px;cursor:pointer;font-size:14px}
 button.green{background:#059669}
 .msg{background:#dcfce7;color:#166534;padding:12px 16px;border-radius:8px;margin-bottom:18px}
 .err{background:#fee2e2;color:#991b1b}
 .tag{padding:3px 9px;border-radius:12px;font-size:12px;background:#dbeafe;color:#1e40af}
 .tag.red{background:#fee2e2;color:#991b1b}.tag.grn{background:#dcfce7;color:#166534}
 form.inline{display:inline}
</style></head><body>
<nav><span class="brand">&#128218; Library Management</span>
 <a href="/" class="{{ 'on' if page=='home' }}">Dashboard</a>
 <a href="/books" class="{{ 'on' if page=='books' }}">Books</a>
 <a href="/members" class="{{ 'on' if page=='members' }}">Members</a>
 <a href="/issue" class="{{ 'on' if page=='issue' }}">Issue Book</a>
 <a href="/issued" class="{{ 'on' if page=='issued' }}">Issued / Return</a>
 <a href="/history" class="{{ 'on' if page=='history' }}">History</a>
</nav>
<div class="wrap">
 {% with msgs = get_flashed_messages(with_categories=true) %}
  {% for cat, m in msgs %}<div class="msg {{ 'err' if cat=='error' }}">{{ m }}</div>{% endfor %}
 {% endwith %}
 {% block body %}{% endblock %}
</div></body></html>
"""

HOME = """{% extends 'base.html' %}{% block body %}
<h2>Dashboard</h2>
<div class="cards">
 <div class="card"><div class="n">{{ s.books }}</div><div class="l">Book titles</div></div>
 <div class="card g"><div class="n">{{ s.members }}</div><div class="l">Members</div></div>
 <div class="card o"><div class="n">{{ s.issued }}</div><div class="l">Currently issued</div></div>
 <div class="card r"><div class="n">{{ s.overdue }}</div><div class="l">Overdue</div></div>
</div>
<div class="box"><h2>Recent activity</h2>
<table><tr><th>Book</th><th>Member</th><th>Issued</th><th>Status</th></tr>
{% for r in recent %}<tr><td>{{ r.title }}</td><td>{{ r.name }}</td><td>{{ r.issue_date }}</td>
<td>{% if r.return_date %}<span class="tag grn">Returned</span>{% else %}<span class="tag">Issued</span>{% endif %}</td></tr>
{% else %}<tr><td colspan="4">No activity yet</td></tr>{% endfor %}</table></div>
{% endblock %}"""

BOOKS = """{% extends 'base.html' %}{% block body %}
<h2>Books</h2>
<div class="box"><form method="post" action="/books/add">
 <input name="title" placeholder="Title" required><input name="author" placeholder="Author" required>
 <input name="category" placeholder="Category"><input name="copies" type="number" min="1" placeholder="Copies" required>
 <button class="green">+ Add Book</button></form></div>
<div class="box"><form method="get"><input name="q" value="{{ q }}" placeholder="Search title / author / category">
 <button>Search</button></form>
<table><tr><th>ID</th><th>Title</th><th>Author</th><th>Category</th><th>Available</th></tr>
{% for b in books %}<tr><td>{{ b.book_id }}</td><td>{{ b.title }}</td><td>{{ b.author }}</td><td>{{ b.category }}</td>
<td><span class="tag {{ 'grn' if b.available_copies>0 else 'red' }}">{{ b.available_copies }} / {{ b.total_copies }}</span></td></tr>
{% else %}<tr><td colspan="5">No books found</td></tr>{% endfor %}</table></div>
{% endblock %}"""

MEMBERS = """{% extends 'base.html' %}{% block body %}
<h2>Members</h2>
<div class="box"><form method="post" action="/members/add">
 <input name="name" placeholder="Name" required><input name="email" type="email" placeholder="Email" required>
 <input name="phone" placeholder="Phone"><button class="green">+ Add Member</button></form></div>
<div class="box"><table><tr><th>ID</th><th>Name</th><th>Email</th><th>Phone</th><th>Joined</th></tr>
{% for m in members %}<tr><td>{{ m.member_id }}</td><td>{{ m.name }}</td><td>{{ m.email }}</td><td>{{ m.phone }}</td><td>{{ m.join_date }}</td></tr>{% endfor %}
</table></div>{% endblock %}"""

ISSUE = """{% extends 'base.html' %}{% block body %}
<h2>Issue a Book</h2>
<div class="box"><form method="post">
 <select name="book_id" required><option value="">-- Select book --</option>
 {% for b in books %}<option value="{{ b.book_id }}">{{ b.title }} ({{ b.available_copies }} available)</option>{% endfor %}</select>
 <select name="member_id" required><option value="">-- Select member --</option>
 {% for m in members %}<option value="{{ m.member_id }}">{{ m.name }}</option>{% endfor %}</select>
 <button class="green">Issue Book</button></form>
 <p style="color:#6b7280">Loan period: {{ days }} days. Fine: Rs {{ fine }} per day after due date.</p></div>
{% endblock %}"""

ISSUED = """{% extends 'base.html' %}{% block body %}
<h2>Currently Issued Books</h2>
<div class="box"><table><tr><th>ID</th><th>Book</th><th>Member</th><th>Issued</th><th>Due</th><th>Status</th><th></th></tr>
{% for r in rows %}<tr class="{{ 'late' if r.late }}"><td>{{ r.issue_id }}</td><td>{{ r.title }}</td><td>{{ r.name }}</td>
<td>{{ r.issue_date }}</td><td>{{ r.due_date }}</td>
<td>{% if r.late %}<span class="tag red">Overdue {{ r.late }} day(s)</span>{% else %}<span class="tag">On time</span>{% endif %}</td>
<td><form class="inline" method="post" action="/return/{{ r.issue_id }}"><button>Return</button></form></td></tr>
{% else %}<tr><td colspan="7">No books currently issued</td></tr>{% endfor %}</table></div>{% endblock %}"""

HISTORY = """{% extends 'base.html' %}{% block body %}
<h2>Issue History</h2>
<div class="box"><table><tr><th>ID</th><th>Book</th><th>Member</th><th>Issued</th><th>Returned</th><th>Fine (Rs)</th></tr>
{% for r in rows %}<tr><td>{{ r.issue_id }}</td><td>{{ r.title }}</td><td>{{ r.name }}</td><td>{{ r.issue_date }}</td>
<td>{{ r.return_date or '-' }}</td><td>{{ r.fine }}</td></tr>{% endfor %}</table></div>{% endblock %}"""

app.jinja_loader = DictLoader({"base.html": BASE, "home.html": HOME, "books.html": BOOKS,
                               "members.html": MEMBERS, "issue.html": ISSUE,
                               "issued.html": ISSUED, "history.html": HISTORY})


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    db = get_db()
    s = {
        "books": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "members": db.execute("SELECT COUNT(*) FROM members").fetchone()[0],
        "issued": db.execute("SELECT COUNT(*) FROM issues WHERE return_date IS NULL").fetchone()[0],
        "overdue": db.execute("SELECT COUNT(*) FROM issues WHERE return_date IS NULL AND due_date < DATE('now')").fetchone()[0],
    }
    recent = db.execute("""SELECT b.title, m.name, i.issue_date, i.return_date FROM issues i
        JOIN books b ON i.book_id=b.book_id JOIN members m ON i.member_id=m.member_id
        ORDER BY i.issue_id DESC LIMIT 5""").fetchall()
    return render_template("home.html", page="home", s=s, recent=recent)


@app.route("/books")
def books():
    q = request.args.get("q", "")
    k = f"%{q}%"
    rows = get_db().execute("""SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR category LIKE ?
                               ORDER BY book_id""", (k, k, k)).fetchall()
    return render_template("books.html", page="books", books=rows, q=q)


@app.route("/books/add", methods=["POST"])
def add_book():
    f = request.form
    db = get_db()
    n = int(f["copies"])
    db.execute("INSERT INTO books (title, author, category, total_copies, available_copies) VALUES (?,?,?,?,?)",
               (f["title"], f["author"], f["category"], n, n))
    db.commit()
    flash("Book added successfully.")
    return redirect(url_for("books"))


@app.route("/members")
def members():
    rows = get_db().execute("SELECT * FROM members ORDER BY member_id").fetchall()
    return render_template("members.html", page="members", members=rows)


@app.route("/members/add", methods=["POST"])
def add_member():
    f = request.form
    db = get_db()
    try:
        db.execute("INSERT INTO members (name, email, phone) VALUES (?,?,?)", (f["name"], f["email"], f["phone"]))
        db.commit()
        flash("Member added successfully.")
    except sqlite3.IntegrityError:
        flash("This email already exists.", "error")
    return redirect(url_for("members"))


@app.route("/issue", methods=["GET", "POST"])
def issue():
    db = get_db()
    if request.method == "POST":
        book_id, member_id = int(request.form["book_id"]), int(request.form["member_id"])
        avail = db.execute("SELECT available_copies FROM books WHERE book_id=?", (book_id,)).fetchone()
        if not avail or avail[0] <= 0:
            flash("No copies available for this book.", "error")
        else:
            due = (date.today() + timedelta(days=LOAN_DAYS)).isoformat()
            db.execute("INSERT INTO issues (book_id, member_id, due_date) VALUES (?,?,?)", (book_id, member_id, due))
            db.commit()
            flash(f"Book issued successfully. Due date: {due}")
        return redirect(url_for("issued"))
    books = db.execute("SELECT * FROM books WHERE available_copies > 0").fetchall()
    mems = db.execute("SELECT * FROM members").fetchall()
    return render_template("issue.html", page="issue", books=books, members=mems, days=LOAN_DAYS, fine=FINE_PER_DAY)


@app.route("/issued")
def issued():
    rows = []
    for r in get_db().execute("""SELECT i.issue_id, b.title, m.name, i.issue_date, i.due_date FROM issues i
        JOIN books b ON i.book_id=b.book_id JOIN members m ON i.member_id=m.member_id
        WHERE i.return_date IS NULL ORDER BY i.due_date""").fetchall():
        late = (date.today() - datetime.strptime(r["due_date"], "%Y-%m-%d").date()).days
        rows.append({**dict(r), "late": late if late > 0 else 0})
    return render_template("issued.html", page="issued", rows=rows)


@app.route("/return/<int:issue_id>", methods=["POST"])
def return_book(issue_id):
    db = get_db()
    row = db.execute("SELECT due_date FROM issues WHERE issue_id=? AND return_date IS NULL", (issue_id,)).fetchone()
    if row:
        late = (date.today() - datetime.strptime(row["due_date"], "%Y-%m-%d").date()).days
        fine = max(0, late) * FINE_PER_DAY
        db.execute("UPDATE issues SET return_date=?, fine=? WHERE issue_id=?", (date.today().isoformat(), fine, issue_id))
        db.commit()
        flash(f"Book returned. Fine: Rs {fine}")
    return redirect(url_for("issued"))


@app.route("/history")
def history():
    rows = get_db().execute("""SELECT i.issue_id, b.title, m.name, i.issue_date, i.return_date, i.fine FROM issues i
        JOIN books b ON i.book_id=b.book_id JOIN members m ON i.member_id=m.member_id
        ORDER BY i.issue_id DESC""").fetchall()
    return render_template("history.html", page="history", rows=rows)


if __name__ == "__main__":
    app.run(debug=True)
