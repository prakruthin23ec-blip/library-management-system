-- Library Management System : Database Schema
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS members (
    member_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT UNIQUE,
    phone       TEXT,
    join_date   TEXT DEFAULT (DATE('now'))
);

CREATE TABLE IF NOT EXISTS books (
    book_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    author           TEXT NOT NULL,
    category         TEXT,
    total_copies     INTEGER NOT NULL CHECK (total_copies >= 0),
    available_copies INTEGER NOT NULL CHECK (available_copies >= 0)
);

CREATE TABLE IF NOT EXISTS issues (
    issue_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id     INTEGER NOT NULL,
    member_id   INTEGER NOT NULL,
    issue_date  TEXT DEFAULT (DATE('now')),
    due_date    TEXT NOT NULL,
    return_date TEXT,
    fine        INTEGER DEFAULT 0,
    FOREIGN KEY (book_id)   REFERENCES books(book_id),
    FOREIGN KEY (member_id) REFERENCES members(member_id)
);

-- Trigger: reduce available copies when a book is issued
CREATE TRIGGER IF NOT EXISTS trg_issue
AFTER INSERT ON issues
BEGIN
    UPDATE books SET available_copies = available_copies - 1
    WHERE book_id = NEW.book_id;
END;

-- Trigger: increase available copies when a book is returned
CREATE TRIGGER IF NOT EXISTS trg_return
AFTER UPDATE OF return_date ON issues
WHEN OLD.return_date IS NULL AND NEW.return_date IS NOT NULL
BEGIN
    UPDATE books SET available_copies = available_copies + 1
    WHERE book_id = NEW.book_id;
END;

-- View: currently issued books
CREATE VIEW IF NOT EXISTS v_current_issues AS
SELECT i.issue_id, b.title, m.name AS member, i.issue_date, i.due_date
FROM issues i
JOIN books b   ON i.book_id = b.book_id
JOIN members m ON i.member_id = m.member_id
WHERE i.return_date IS NULL;

-- Sample data
INSERT OR IGNORE INTO members (member_id, name, email, phone) VALUES
 (1, 'Ananya Rao',  'ananya@example.com', '9876543210'),
 (2, 'Rahul Kumar', 'rahul@example.com',  '9123456780');

INSERT OR IGNORE INTO books (book_id, title, author, category, total_copies, available_copies) VALUES
 (1, 'Database System Concepts', 'Silberschatz', 'DBMS', 3, 3),
 (2, 'Fundamentals of Database Systems', 'Elmasri & Navathe', 'DBMS', 2, 2),
 (3, 'Electronic Devices and Circuits', 'Boylestad', 'ECE', 2, 2),
 (4, 'Signals and Systems', 'Oppenheim', 'ECE', 1, 1);
