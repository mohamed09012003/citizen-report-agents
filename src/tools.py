import math
from datetime import date

from database import get_connection

VALID_URGENCIES = ["low", "medium", "high", "emergency"]


# ---------- Helper functions (used by the tools, not given to the agents) ----------


def _distance_km(lat1, lon1, lat2, lon2):
    """Straight-line distance between two points in kilometres (haversine formula)."""
    r = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _find_street(conn, street):
    """Return the street row (case-insensitive), or None if it does not exist."""
    return conn.execute(
        "SELECT * FROM streets WHERE LOWER(name) = LOWER(?)", (street,)
    ).fetchone()


# ---------- Tools (given to the agents) ----------


def get_categories() -> str:
    """List all allowed problem categories and the department responsible for each.

    Returns:
        A list of categories with their departments
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, name FROM departments ORDER BY category"
    ).fetchall()
    conn.close()
    lines = [f"- {r['category']}: {r['name']}" for r in rows]
    return "Allowed categories and their departments:\n" + "\n".join(lines)


def find_similar_tickets(street: str, category: str) -> str:
    """Check whether an open ticket already exists for the same problem on the same street.
    Use this to detect duplicate reports.

    Args:
        street: The street name from the citizen report, e.g. Ringstraße
        category: The problem category, e.g. pothole, streetlight, garbage

    Returns:
        Matching open tickets, or a message that none were found
    """
    conn = get_connection()
    if _find_street(conn, street) is None:
        conn.close()
        return f"Unknown street '{street}'. Please use the exact street name from the report."

    rows = conn.execute(
        """SELECT ticket_id, category, street, description, created_at FROM tickets
           WHERE LOWER(street) = LOWER(?) AND LOWER(category) = LOWER(?) AND status = 'open'""",
        (street, category),
    ).fetchall()
    conn.close()

    if not rows:
        return f"No open {category} tickets on {street}. This is a new problem."
    lines = [
        f"- Ticket #{r['ticket_id']}: {r['category']} on {r['street']}, "
        f"'{r['description']}' (reported {r['created_at']})"
        for r in rows
    ]
    return "Open tickets found for the same problem:\n" + "\n".join(lines)


def get_available_crews(department: str, street: str) -> str:
    """List the free repair crews of a department, sorted by distance to the problem.

    Args:
        department: The responsible department, e.g. Road Maintenance
        street: The street where the problem is

    Returns:
        Available crews with their distance in km, nearest first
    """
    conn = get_connection()
    target = _find_street(conn, street)
    if target is None:
        conn.close()
        return f"Unknown street '{street}'."

    dept = conn.execute(
        "SELECT name FROM departments WHERE LOWER(name) = LOWER(?)", (department,)
    ).fetchone()
    if dept is None:
        valid = [r["name"] for r in conn.execute("SELECT name FROM departments")]
        conn.close()
        return (
            f"Unknown department '{department}'. Valid departments: {', '.join(valid)}."
        )

    crews = conn.execute(
        """SELECT c.name, s.latitude, s.longitude FROM crews c
           JOIN streets s ON s.name = c.base_street
           WHERE c.department = ? AND c.available = 1""",
        (dept["name"],),
    ).fetchall()
    conn.close()

    if not crews:
        return f"No crews of {dept['name']} are available right now. The ticket will wait in the queue."

    ranked = sorted(
        crews,
        key=lambda c: _distance_km(
            c["latitude"], c["longitude"], target["latitude"], target["longitude"]
        ),
    )
    lines = []
    for c in ranked:
        km = _distance_km(
            c["latitude"], c["longitude"], target["latitude"], target["longitude"]
        )
        lines.append(f"- {c['name']}: {km:.1f} km away")
    return f"Available crews of {dept['name']} (nearest first):\n" + "\n".join(lines)


def create_ticket(
    category: str,
    street: str,
    description: str,
    urgency: str,
    department: str,
    crew: str = "",
) -> str:
    """Create a new repair ticket and assign a crew to it.

    Args:
        category: The problem category, e.g. pothole
        street: The street where the problem is
        description: A short description of the problem
        urgency: One of low, medium, high, emergency
        department: The responsible department
        crew: The name of the crew to assign, or empty if no crew is available

    Returns:
        Confirmation with the new ticket number, or an error message
    """
    conn = get_connection()

    # Check every input before saving anything
    street_row = _find_street(conn, street)
    dept = conn.execute(
        "SELECT name, category FROM departments WHERE LOWER(name) = LOWER(?)",
        (department,),
    ).fetchone()
    errors = []
    if street_row is None:
        errors.append(f"unknown street '{street}'")
    if dept is None:
        errors.append(f"unknown department '{department}'")
    elif dept["category"] != category.lower():
        errors.append(f"category '{category}' does not belong to {dept['name']}")
    if urgency.lower() not in VALID_URGENCIES:
        errors.append(f"urgency must be one of {', '.join(VALID_URGENCIES)}")

    crew_row = None
    if crew:
        crew_row = conn.execute(
            "SELECT name, department, available FROM crews WHERE LOWER(name) = LOWER(?)",
            (crew,),
        ).fetchone()
        if crew_row is None:
            errors.append(f"unknown crew '{crew}'")
        elif dept is not None and crew_row["department"] != dept["name"]:
            errors.append(f"{crew_row['name']} does not belong to {dept['name']}")
        elif not crew_row["available"]:
            errors.append(f"{crew_row['name']} is not available")

    if errors:
        conn.close()
        return "Ticket NOT created. Problems: " + "; ".join(errors) + "."

    # Save the ticket and mark the crew as busy
    cursor = conn.execute(
        """INSERT INTO tickets (category, street, description, urgency, department, crew, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'open', ?)""",
        (
            category.lower(),
            street_row["name"],
            description,
            urgency.lower(),
            dept["name"],
            crew_row["name"] if crew_row else None,
            date.today().isoformat(),
        ),
    )
    if crew_row:
        conn.execute(
            "UPDATE crews SET available = 0 WHERE name = ?", (crew_row["name"],)
        )
    conn.commit()
    ticket_id = cursor.lastrowid
    conn.close()

    assigned = crew_row["name"] if crew_row else "no crew yet (waiting in queue)"
    return f"Ticket #{ticket_id} created: {category} on {street_row['name']}, urgency {urgency}, assigned to {assigned}."


# ---------- Quick test ----------

if __name__ == "__main__":
    from database import reset_database

    reset_database()

    print(get_categories(), "\n")
    print(find_similar_tickets("Ringstraße", "pothole"), "\n")  # duplicate
    print(find_similar_tickets("Feldstraße", "pothole"), "\n")  # new problem
    print(get_available_crews("Road Maintenance", "Feldstraße"), "\n")
    print(
        create_ticket(
            "pothole",
            "Feldstraße",
            "Large pothole in front of the bakery",
            "high",
            "Road Maintenance",
            "Road Crew 2",
        ),
        "\n",
    )
    print(
        get_available_crews("Road Maintenance", "Feldstraße"), "\n"
    )  # Crew 2 now busy
    print(
        create_ticket("pothole", "Fakestraße", "Test", "urgent", "Road Repair"), "\n"
    )  # errors
