"""Library Management System - Python + SQLite (command line)"""
import sqlite3
import os
from datetime import date, timedelta, datetime

DB = "library.db"
LOAN_DAYS = 14
FINE_PER_DAY = 2  # Rs per day


def connect():
    first_time = not os.path.exists(DB)
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")
    if first_time:
        with open("schema.sql") as f:
            conn.executescript(f.read())
    return conn


def show(rows, headers):
    if not rows:
        print("  (no records)")
        return
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) for i, h in enumerate(headers)]
    line = " | ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print("\n" + line)
    print("-" * len(line))
    for r in rows:
        print(" | ".join(str(c).ljust(w) for c, w in zip(r, widths)))


def add_book(conn):
    title = input("Title: ")
    author = input("Author: ")
    cat = input("Category: ")
    copies = int(input("Number of copies: "))
    conn.execute("INSERT INTO books (title, author, category, total_copies, available_copies) VALUES (?,?,?,?,?)",
                 (title, author, cat, copies, copies))
    conn.commit()
    print("Book added.")


def add_member(conn):
    name = input("Name: ")
    email = input("Email: ")
    phone = input("Phone: ")
    try:
        conn.execute("INSERT INTO members (name, email, phone) VALUES (?,?,?)", (name, email, phone))
        conn.commit()
        print("Member added.")
    except sqlite3.IntegrityError:
        print("Error: this email already exists.")


def view_books(conn):
    rows = conn.execute("SELECT book_id, title, author, category, available_copies, total_copies FROM books").fetchall()
    show(rows, ["ID", "Title", "Author", "Category", "Available", "Total"])


def view_members(conn):
    rows = conn.execute("SELECT member_id, name, email, phone FROM members").fetchall()
    show(rows, ["ID", "Name", "Email", "Phone"])


def search_book(conn):
    kw = "%" + input("Search by title/author/category: ") + "%"
    rows = conn.execute("""SELECT book_id, title, author, category, available_copies FROM books
                           WHERE title LIKE ? OR author LIKE ? OR category LIKE ?""", (kw, kw, kw)).fetchall()
    show(rows, ["ID", "Title", "Author", "Category", "Available"])


def issue_book(conn):
    book_id = int(input("Book ID: "))
    member_id = int(input("Member ID: "))
    book = conn.execute("SELECT available_copies FROM books WHERE book_id=?", (book_id,)).fetchone()
    member = conn.execute("SELECT 1 FROM members WHERE member_id=?", (member_id,)).fetchone()
    if not book or not member:
        print("Invalid book or member ID.")
        return
    if book[0] <= 0:
        print("Sorry, no copies available.")
        return
    due = (date.today() + timedelta(days=LOAN_DAYS)).isoformat()
    conn.execute("INSERT INTO issues (book_id, member_id, due_date) VALUES (?,?,?)", (book_id, member_id, due))
    conn.commit()
    print(f"Book issued. Due date: {due}")


def return_book(conn):
    issue_id = int(input("Issue ID: "))
    row = conn.execute("SELECT due_date FROM issues WHERE issue_id=? AND return_date IS NULL", (issue_id,)).fetchone()
    if not row:
        print("No active issue with that ID.")
        return
    due = datetime.strptime(row[0], "%Y-%m-%d").date()
    late = (date.today() - due).days
    fine = max(0, late) * FINE_PER_DAY
    conn.execute("UPDATE issues SET return_date=?, fine=? WHERE issue_id=?",
                 (date.today().isoformat(), fine, issue_id))
    conn.commit()
    print(f"Book returned. Fine: Rs {fine}")


def current_issues(conn):
    rows = conn.execute("SELECT * FROM v_current_issues").fetchall()
    show(rows, ["Issue ID", "Book", "Member", "Issued", "Due"])


def overdue(conn):
    rows = conn.execute("""SELECT i.issue_id, b.title, m.name, i.due_date
                           FROM issues i JOIN books b ON i.book_id=b.book_id
                           JOIN members m ON i.member_id=m.member_id
                           WHERE i.return_date IS NULL AND i.due_date < DATE('now')""").fetchall()
    show(rows, ["Issue ID", "Book", "Member", "Due Date"])


def history(conn):
    rows = conn.execute("""SELECT i.issue_id, b.title, m.name, i.issue_date, i.return_date, i.fine
                           FROM issues i JOIN books b ON i.book_id=b.book_id
                           JOIN members m ON i.member_id=m.member_id""").fetchall()
    show(rows, ["Issue ID", "Book", "Member", "Issued", "Returned", "Fine"])


MENU = """
===== LIBRARY MANAGEMENT SYSTEM =====
1. Add book            6. Issue book
2. Add member          7. Return book
3. View books          8. Currently issued books
4. View members        9. Overdue books
5. Search book        10. Issue history
0. Exit
"""
ACTIONS = {"1": add_book, "2": add_member, "3": view_books, "4": view_members, "5": search_book,
           "6": issue_book, "7": return_book, "8": current_issues, "9": overdue, "10": history}


def main():
    conn = connect()
    while True:
        print(MENU)
        choice = input("Enter choice: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        action = ACTIONS.get(choice)
        if not action:
            print("Invalid choice.")
            continue
        try:
            action(conn)
        except ValueError:
            print("Please enter a valid number.")


if __name__ == "__main__":
    main()
