"""SQLite: lưu phường/xã, công ty (khóa MST => tự lọc trùng) và lượt xuất hiện để tính tỷ lệ trùng."""
import os
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    path TEXT PRIMARY KEY,
    province TEXT,
    status TEXT DEFAULT 'pending',   -- pending | done
    pages INTEGER DEFAULT 0,
    rows INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS companies (
    mst TEXT PRIMARY KEY,
    name TEXT,
    first_location TEXT,
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hits (
    mst TEXT,
    location TEXT,
    PRIMARY KEY (mst, location)
);
"""


class Store:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()

    def add_locations(self, rows):
        with self.lock, self.db:
            self.db.executemany("INSERT OR IGNORE INTO locations(path, province) VALUES (?, ?)", rows)

    def pending(self, province=None):
        q = "SELECT path FROM locations WHERE status='pending'"
        args = ()
        if province:
            q += " AND province LIKE ?"
            args = (f"%{province}%",)
        return [r[0] for r in self.db.execute(q + " ORDER BY path", args)]

    def save_location(self, path, pages, items):
        with self.lock, self.db:
            self.db.executemany("INSERT OR IGNORE INTO companies(mst, name, first_location) VALUES (?, ?, ?)",
                                [(c["mst"], c["name"], path) for c in items])
            self.db.executemany("INSERT OR IGNORE INTO hits(mst, location) VALUES (?, ?)",
                                [(c["mst"], path) for c in items])
            self.db.execute("UPDATE locations SET status='done', pages=?, rows=? WHERE path=?",
                            (pages, len(items), path))

    def stats(self):
        one = lambda q: self.db.execute(q).fetchone()[0]
        return {
            "locations_total": one("SELECT COUNT(*) FROM locations"),
            "locations_done": one("SELECT COUNT(*) FROM locations WHERE status='done'"),
            "locations_capped": one("SELECT COUNT(*) FROM locations WHERE pages>=10"),
            "rows_total": one("SELECT COUNT(*) FROM hits"),
            "companies_unique": one("SELECT COUNT(*) FROM companies"),
        }
