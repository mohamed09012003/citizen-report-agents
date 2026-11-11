import sqlite3
from pathlib import Path

import pandas as pd

# Paths work no matter where you run the script from
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "city.db"


def get_connection():
    """Open a connection to the city database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def create_tables(conn):
    """Create the four tables of the simulated city."""
    conn.executescript("""
        CREATE TABLE departments (
            name     TEXT PRIMARY KEY,
            category TEXT UNIQUE NOT NULL
        );

        CREATE TABLE streets (
            name      TEXT PRIMARY KEY,
            latitude  REAL NOT NULL,
            longitude REAL NOT NULL
        );

        CREATE TABLE crews (
            name        TEXT PRIMARY KEY,
            department  TEXT NOT NULL REFERENCES departments(name),
            base_street TEXT NOT NULL REFERENCES streets(name),
            available   INTEGER NOT NULL      -- 1 = free, 0 = busy
        );

        CREATE TABLE tickets (
            ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT NOT NULL,
            street      TEXT NOT NULL REFERENCES streets(name),
            description TEXT,
            urgency     TEXT,
            department  TEXT REFERENCES departments(name),
            crew        TEXT REFERENCES crews(name),
            status      TEXT NOT NULL DEFAULT 'open',   -- open / fixed
            created_at  TEXT NOT NULL
        );
    """)


def load_data(conn):
    """Fill the tables from the CSV files in the data folder."""
    departments = pd.read_csv(DATA_DIR / "departments.csv", encoding="utf-8-sig")
    streets = pd.read_csv(DATA_DIR / "streets.csv", encoding="utf-8-sig")
    crews = pd.read_csv(DATA_DIR / "crews.csv", encoding="utf-8-sig")
    tickets = pd.read_csv(DATA_DIR / "seed_tickets.csv", encoding="utf-8-sig")

    conn.executemany(
        "INSERT INTO departments (name, category) VALUES (?, ?)",
        departments[["department", "category"]].values.tolist(),
    )
    conn.executemany(
        "INSERT INTO streets (name, latitude, longitude) VALUES (?, ?, ?)",
        streets[["street", "latitude", "longitude"]].values.tolist(),
    )
    conn.executemany(
        "INSERT INTO crews (name, department, base_street, available) VALUES (?, ?, ?, ?)",
        crews[["crew", "department", "base_street", "available"]].values.tolist(),
    )

    # Seed tickets get their department from the category
    dept_by_category = dict(zip(departments["category"], departments["department"]))
    for _, t in tickets.iterrows():
        conn.execute(
            """INSERT INTO tickets
               (ticket_id, category, street, description, department, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                int(t["ticket_id"]),
                t["category"],
                t["street"],
                t["description"],
                dept_by_category[t["category"]],
                t["status"],
                t["created_at"],
            ),
        )
    conn.commit()


def reset_database():
    """Delete the database and rebuild it from the CSV files (the starting state)."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = get_connection()
    create_tables(conn)
    load_data(conn)
    conn.close()


if __name__ == "__main__":
    # Build the database and print a quick summary
    reset_database()
    conn = get_connection()
    for table in ["departments", "streets", "crews", "tickets"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")

    print("\nOpen tickets on Ringstraße:")
    for row in conn.execute("SELECT * FROM tickets WHERE street = 'Ringstraße'"):
        print(dict(row))
    conn.close()
