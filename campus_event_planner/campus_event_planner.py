"""
Campus Event Planner
Course: Computational Thinking and Programming (2026CSAE100)
Team: Shreyansh Kumar, Pranshu Rai, Mudita Choudhary, Advika Chamoli, Yugant Rathi

A menu-driven console program that manages campus events and student
registrations in CSV files. It detects venue clashes, blocks duplicate and
over-capacity registrations, and summarises demand.

Run:  python campus_event_planner.py
Only the Python standard library is used.
"""

import csv
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
EVENTS_FILE = BASE_DIR / "events.csv"
REGS_FILE = BASE_DIR / "registrations.csv"

EVENT_FIELDS = ["event_id", "title", "category", "date", "start_time",
                "end_time", "venue", "capacity", "status"]
REG_FIELDS = ["registration_id", "event_id", "student_id", "student_name",
              "email", "timestamp"]

OPEN = "Open"
CANCELLED = "Cancelled"

HIGH_DEMAND = 0.75   # occupancy at or above this  -> "High demand"
FILLING = 0.40       # occupancy at or above this  -> "Filling"

# Fictional sample data, written only when the CSV files do not exist yet.
SAMPLE_EVENTS = [
    {"event_id": "E001", "title": "Python for Everyone", "category": "Workshop",
     "date": "2026-12-05", "start_time": "10:00", "end_time": "13:00",
     "venue": "Computer Lab 2", "capacity": "40", "status": OPEN},
    {"event_id": "E002", "title": "Campus Open Mic", "category": "Cultural",
     "date": "2026-12-06", "start_time": "17:00", "end_time": "20:00",
     "venue": "Open Air Theatre", "capacity": "80", "status": OPEN},
    {"event_id": "E003", "title": "Sustainable Campus Forum", "category": "Seminar",
     "date": "2026-12-08", "start_time": "11:00", "end_time": "12:30",
     "venue": "Seminar Hall A", "capacity": "60", "status": OPEN},
]
SAMPLE_REGS = [
    {"registration_id": "R001", "event_id": "E001", "student_id": "S26CSEU1001",
     "student_name": "Aarav Mehta", "email": "aarav.mehta@example.edu",
     "timestamp": "2026-11-20 09:15:00"},
    {"registration_id": "R002", "event_id": "E001", "student_id": "S26CSEU1002",
     "student_name": "Diya Nair", "email": "diya.nair@example.edu",
     "timestamp": "2026-11-20 09:42:10"},
    {"registration_id": "R003", "event_id": "E002", "student_id": "S26CSEU1003",
     "student_name": "Kabir Singh", "email": "kabir.singh@example.edu",
     "timestamp": "2026-11-21 14:05:33"},
]


# ----------------------------------------------------------------------------
# CSV storage
# ----------------------------------------------------------------------------
def save_csv(path, fields, rows):
    """Write a list of dictionaries to a CSV file with a header row."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def load_csv(path):
    """Read a CSV file into a list of dictionaries ([] if it is missing)."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def ensure_files():
    """Create missing CSV files with headers and fictional sample rows."""
    if not EVENTS_FILE.exists():
        save_csv(EVENTS_FILE, EVENT_FIELDS, SAMPLE_EVENTS)
    if not REGS_FILE.exists():
        save_csv(REGS_FILE, REG_FIELDS, SAMPLE_REGS)


def load_events():
    return load_csv(EVENTS_FILE)


def load_registrations():
    return load_csv(REGS_FILE)


# ----------------------------------------------------------------------------
# Small helpers and validation
# ----------------------------------------------------------------------------
def next_id(rows, key, prefix):
    """Return the next sequential ID, e.g. highest E010 -> E011."""
    highest = 0
    for row in rows:
        try:
            highest = max(highest, int(row[key][len(prefix):]))
        except (ValueError, KeyError, TypeError):
            continue  # ignore malformed IDs instead of crashing
    return f"{prefix}{highest + 1:03d}"


def parse_date(text):
    """'2026-12-05' -> date object, or None if the text is not a valid date."""
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_time(text):
    """'14:30' -> time object, or None if the text is not a valid 24h time."""
    try:
        return datetime.strptime(text.strip(), "%H:%M").time()
    except ValueError:
        return None


def is_valid_email(email):
    """Basic shape check: one '@', text before it, a dot inside the domain."""
    email = email.strip()
    if " " in email or email.count("@") != 1:
        return False
    local, domain = email.split("@")
    return bool(local) and "." in domain and not domain.startswith(".") \
        and not domain.endswith(".")


def count_registrations(registrations, event_id):
    """Number of registrations for one event (generator expression)."""
    return sum(1 for r in registrations if r["event_id"] == event_id)


def find_event(events, event_id):
    """Return the event with this ID (case-insensitive) or None."""
    for event in events:
        if event["event_id"].upper() == event_id.strip().upper():
            return event
    return None


def open_events(events):
    return [e for e in events if e["status"] == OPEN]


# ----------------------------------------------------------------------------
# Core rules (no input()/print() so they are easy to test)
# ----------------------------------------------------------------------------
def times_overlap(new_start, new_end, old_start, old_end):
    """Half-open interval overlap: new_start < old_end and old_start < new_end.
    An event ending at 12:00 and another starting at 12:00 do NOT overlap."""
    return new_start < old_end and old_start < new_end


def find_venue_conflict(events, venue, date, start, end):
    """Return the first non-cancelled event that clashes, else None.
    venue is compared case-insensitively; date/start/end are strings."""
    new_start, new_end = parse_time(start), parse_time(end)
    for event in events:
        if event["status"] == CANCELLED:
            continue
        if event["venue"].strip().lower() != venue.strip().lower():
            continue
        if event["date"] != date:
            continue
        if times_overlap(new_start, new_end,
                         parse_time(event["start_time"]),
                         parse_time(event["end_time"])):
            return event
    return None


def build_event(events, title, category, date, start, end, venue, capacity):
    """Validate input and return (new_event_dict, None) or (None, error)."""
    if not title.strip() or not category.strip() or not venue.strip():
        return None, "Title, category and venue cannot be empty."
    if parse_date(date) is None:
        return None, "Date must be a real date in YYYY-MM-DD format."
    t_start, t_end = parse_time(start), parse_time(end)
    if t_start is None or t_end is None:
        return None, "Times must be in 24-hour HH:MM format."
    if t_end <= t_start:
        return None, "End time must be later than start time."
    try:
        seats = int(capacity)
    except ValueError:
        return None, "Capacity must be a whole number."
    if seats <= 0:
        return None, "Capacity must be a positive number."

    start, end = t_start.strftime("%H:%M"), t_end.strftime("%H:%M")
    date = parse_date(date).isoformat()
    clash = find_venue_conflict(events, venue, date, start, end)
    if clash:
        return None, (f"Venue conflict with {clash['event_id']} "
                      f"'{clash['title']}' ({clash['start_time']}-"
                      f"{clash['end_time']}) at {clash['venue']} on {date}.")

    event = {"event_id": next_id(events, "event_id", "E"),
             "title": title.strip(), "category": category.strip().title(),
             "date": date, "start_time": start, "end_time": end,
             "venue": venue.strip(), "capacity": str(seats), "status": OPEN}
    return event, None


def build_registration(events, registrations, event_id, student_id, name, email):
    """Check every registration rule. Returns (new_row, None) or (None, error)."""
    event = find_event(events, event_id)
    if event is None:
        return None, f"No event found with ID '{event_id.strip()}'."
    if event["status"] != OPEN:
        return None, f"Event {event['event_id']} is {event['status']} and cannot take registrations."
    student_id = student_id.strip().upper()
    if not student_id or not name.strip():
        return None, "Student ID and name cannot be empty."
    if any(r["event_id"] == event["event_id"] and r["student_id"] == student_id
           for r in registrations):
        return None, f"Student {student_id} is already registered for {event['event_id']}."
    if count_registrations(registrations, event["event_id"]) >= int(event["capacity"]):
        return None, f"Event {event['event_id']} is full ({event['capacity']}/{event['capacity']} seats)."
    if not is_valid_email(email):
        return None, "Email address looks invalid (expected name@domain.com)."

    row = {"registration_id": next_id(registrations, "registration_id", "R"),
           "event_id": event["event_id"], "student_id": student_id,
           "student_name": name.strip(), "email": email.strip(),
           "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    return row, None


def demand_summary(events, registrations):
    """Return (ranking, category_totals, total_regs, total_capacity)
    for all open events."""
    ranking = []
    category_totals = {}
    for event in open_events(events):
        regs = count_registrations(registrations, event["event_id"])
        capacity = int(event["capacity"])
        ranking.append({"event": event, "registrations": regs,
                        "capacity": capacity, "occupancy": regs / capacity})
        category_totals[event["category"]] = \
            category_totals.get(event["category"], 0) + regs
    # highest occupancy first; registration count breaks ties
    ranking.sort(key=lambda r: (r["occupancy"], r["registrations"]), reverse=True)
    total_regs = sum(r["registrations"] for r in ranking)
    total_cap = sum(r["capacity"] for r in ranking)
    return ranking, category_totals, total_regs, total_cap


def demand_guidance(occupancy):
    """Rule-based label from the occupancy ratio."""
    if occupancy >= HIGH_DEMAND:
        return "High demand"
    if occupancy >= FILLING:
        return "Filling"
    return "More promotion may help"


# ----------------------------------------------------------------------------
# Menu features (these talk to the user)
# ----------------------------------------------------------------------------
def list_events():
    events, regs = load_events(), load_registrations()
    active = sorted(open_events(events),
                    key=lambda e: (e["date"], e["start_time"]))
    print("\n=== Upcoming Events ===")
    if not active:
        print("No active events.")
        return
    for e in active:
        taken = count_registrations(regs, e["event_id"])
        left = int(e["capacity"]) - taken
        print(f"{e['event_id']} | {e['title']} [{e['category']}]")
        print(f"     {e['date']} {e['start_time']}-{e['end_time']} @ {e['venue']}"
              f" | Seats left: {left}/{e['capacity']}")


def create_event():
    events = load_events()
    print("\n=== Create Event ===")
    event, error = build_event(
        events,
        input("Title: "), input("Category (e.g. Workshop, Cultural): "),
        input("Date (YYYY-MM-DD): "), input("Start time (HH:MM, 24h): "),
        input("End time (HH:MM, 24h): "), input("Venue: "),
        input("Capacity: "))
    if error:
        print(f"Event not created: {error}")
        return
    events.append(event)
    save_csv(EVENTS_FILE, EVENT_FIELDS, events)
    print(f"Event created with ID {event['event_id']}.")


def register_student():
    events, regs = load_events(), load_registrations()
    print("\n=== Register Student ===")
    if not open_events(events):
        print("There are no open events.")
        return
    list_events()
    row, error = build_registration(
        events, regs,
        input("\nEvent ID: "), input("Student ID: "),
        input("Student name: "), input("Email: "))
    if error:
        print(f"Registration failed: {error}")
        return
    regs.append(row)
    save_csv(REGS_FILE, REG_FIELDS, regs)
    event = find_event(events, row["event_id"])
    left = int(event["capacity"]) - count_registrations(regs, event["event_id"])
    print(f"Registered {row['student_name']} for '{event['title']}' "
          f"(ID {row['registration_id']}). Seats left: {left}.")


def cancel_event():
    events, regs = load_events(), load_registrations()
    print("\n=== Cancel Event ===")
    list_events()
    event = find_event(events, input("\nEvent ID to cancel: "))
    if event is None:
        print("Cancellation failed: no event with that ID.")
        return
    if event["status"] == CANCELLED:
        print(f"Event {event['event_id']} is already cancelled.")
        return
    booked = count_registrations(regs, event["event_id"])
    answer = input(f"Cancel '{event['title']}' ({booked} registrations kept "
                   f"on record)? (y/n): ").strip().lower()
    if answer != "y":
        print("Cancellation aborted.")
        return
    event["status"] = CANCELLED
    save_csv(EVENTS_FILE, EVENT_FIELDS, events)
    print(f"Event {event['event_id']} marked as Cancelled. Records retained.")


def demand_report():
    events, regs = load_events(), load_registrations()
    ranking, categories, total_regs, total_cap = demand_summary(events, regs)
    print("\n=== Demand Report ===")
    if not ranking:
        print("No open events to analyse.")
        return
    overall = total_regs / total_cap * 100
    print(f"Open events: {len(ranking)} | Registrations: {total_regs} | "
          f"Overall occupancy: {overall:.1f}%")
    print("\nRanking by occupancy:")
    for i, r in enumerate(ranking, start=1):
        print(f"{i}. {r['event']['title']} - {r['registrations']}/{r['capacity']} "
              f"seats ({r['occupancy'] * 100:.0f}%) - "
              f"{demand_guidance(r['occupancy'])}")
    print("\nRegistrations by category:")
    for category, count in sorted(categories.items(),
                                  key=lambda item: item[1], reverse=True):
        print(f"  {category}: {count}")


# ----------------------------------------------------------------------------
# Main menu
# ----------------------------------------------------------------------------
MENU = """
==============================
   CAMPUS EVENT PLANNER
==============================
1. List upcoming events
2. Create a new event
3. Register a student
4. Cancel an event
5. Demand report
0. Exit"""

ACTIONS = {"1": list_events, "2": create_event, "3": register_student,
           "4": cancel_event, "5": demand_report}


def main():
    ensure_files()
    while True:
        print(MENU)
        try:
            choice = input("Choose an option: ").strip()
        except EOFError:           # input stream ended (e.g. piped input)
            break
        if choice == "0":
            break
        action = ACTIONS.get(choice)
        if action is None:
            print("Invalid option. Please enter a number from 0 to 5.")
            continue
        try:
            action()
        except EOFError:
            break
        except OSError as err:     # file missing/locked/permission problem
            print(f"File error: {err}")
    print("Goodbye!")


if __name__ == "__main__":
    main()
