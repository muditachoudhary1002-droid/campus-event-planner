"""
Runs the 12 interactive test scenarios against the real program, using a fresh
temporary copy of the data for each one (your real CSV files are never touched).
Writes:  testing_plan.csv  and  demo_transcript.txt

Run:  python run_scenarios.py
"""
import builtins
import contextlib
import csv
import io
import tempfile
from pathlib import Path

import campus_event_planner as cep

HERE = Path(__file__).resolve().parent


def run_session(answers):
    """Run main() once, feeding `answers` to input() and echoing them like a
    real terminal. Returns everything that was printed."""
    feed = iter(answers)
    buf = io.StringIO()

    def fake_input(prompt=""):
        try:
            value = next(feed)
        except StopIteration:
            raise EOFError
        buf.write(f"{prompt}{value}\n")
        return value

    real_input = builtins.input
    builtins.input = fake_input
    try:
        with contextlib.redirect_stdout(buf):
            cep.main()
    finally:
        builtins.input = real_input
    return buf.getvalue()


def new_event(title, cat, date, start, end, venue, cap):
    return ["2", title, cat, date, start, end, venue, cap]


def register(eid, sid, name, email):
    return ["3", eid, sid, name, email]


# Each scenario: (feature, kind, description, input summary, expected,
#                 [sessions], check(output, events, regs) -> (bool, actual))
def s1(out, ev, rg):
    ok = ("Open events: 3 | Registrations: 3 | Overall occupancy: 1.7%" in out
          and "Python for Everyone - 2/40 seats (5%)" in out)
    return ok, "3 events listed by date; report: 3 open events, 3 registrations, 1.7% occupancy"


def s2(out, ev, rg):
    ok = "Event created with ID E004" in out and len(ev) == 4 and ev[-1]["status"] == "Open"
    return ok, "Event E004 created and saved to events.csv (4 rows)"


def s3(out, ev, rg):
    ok = "Event created with ID E004" in out
    return ok, "New 13:00-14:00 event accepted next to E001 (ends 13:00) in the same venue"


def s4(out, ev, rg):
    ok = "Venue conflict with E001" in out and len(ev) == 3
    return ok, "Blocked: 'Venue conflict with E001' (venue typed in lower case); events.csv unchanged"


def s5(out, ev, rg):
    errs = ["real date", "24-hour", "later than start", "positive", "whole number"]
    ok = all(e in out for e in errs) and len(ev) == 3
    return ok, "Each of 5 bad inputs rejected with its own message; no event saved"


def s6(out, ev, rg):
    ok = "Seats left: 59" in out and len(rg) == 4 and rg[-1]["student_id"] == "S26CSEU1374"
    return ok, "Registered as R004; 'Seats left: 59'; row appended to registrations.csv"


def s7(out, ev, rg):
    ok = "already registered" in out and len(rg) == 3
    return ok, "Blocked: 'already registered for E001'; registrations.csv unchanged"


def s8(out, ev, rg):
    ok = "is full (1/1 seats)" in out and len(rg) == 4
    return ok, "1st student accepted; 2nd blocked: 'Event E004 is full (1/1 seats)'"


def s9(out, ev, rg):
    ok = "Email address looks invalid" in out and len(rg) == 3
    return ok, "Blocked: 'Email address looks invalid'; nothing saved"


def s10(out, ev, rg):
    e2 = next(e for e in ev if e["event_id"] == "E002")
    after = out.split("Event E002 marked as Cancelled")[1].split("Choose an option: 3")[0]
    ok = (e2["status"] == "Cancelled" and "Campus Open Mic" not in after
          and "Event E002 is Cancelled and cannot take registrations" in out
          and any(r["event_id"] == "E002" for r in rg))
    return ok, ("E002 status -> Cancelled; its registration R003 kept in CSV; "
                "no longer listed; new registration refused")


def s11(out, ev, rg):
    ok = out.count("Invalid option") == 3 and "Goodbye!" in out
    return ok, "'abc', '9' and blank each give 'Invalid option'; program keeps running and exits on 0"


def s12(out, ev, rg):
    ok = ("Registrations: 4" in out and "Sustainable Campus Forum - 1/60" in out
          and len(rg) == 4)
    return ok, "After closing and restarting: 4 registrations remembered; report shows E003 at 1/60"


SCENARIOS = [
    ("Startup and analytics", "Normal",
     "First launch with the fictional sample files; list events and open demand report",
     "Menu 1, then 5", "3 events listed; 3 registrations / 180 seats = 1.7%",
     [["1", "5", "0"]], s1),
    ("Event creation", "Normal",
     "Create a valid event in a free venue",
     "Hackathon Kickoff, 2026-12-10, 10:00-12:00, Main Auditorium, 50",
     "Event E004 created and saved",
     [new_event("Hackathon Kickoff", "Competition", "2026-12-10", "10:00", "12:00",
                "Main Auditorium", "50") + ["0"]], s2),
    ("Venue conflict", "Boundary",
     "New event starts exactly when another ends in the same venue",
     "Computer Lab 2, 2026-12-05, 13:00-14:00 (E001 ends 13:00)",
     "Accepted: half-open intervals allow back-to-back events",
     [new_event("Doubt Clinic", "Workshop", "2026-12-05", "13:00", "14:00",
                "Computer Lab 2", "30") + ["0"]], s3),
    ("Venue conflict", "Invalid",
     "New event overlaps an existing one; venue typed in different letter case",
     "computer lab 2, 2026-12-05, 11:00-12:00",
     "Rejected with venue conflict message",
     [new_event("Clash", "Workshop", "2026-12-05", "11:00", "12:00",
                "computer lab 2", "30") + ["0"]], s4),
    ("Event creation", "Invalid",
     "Impossible date, bad time, end before start, zero capacity, non-numeric capacity",
     "2026-02-30; 25:00; 11:00-10:00; capacity 0; capacity abc",
     "Each input rejected with a clear message; nothing saved",
     [new_event("X", "Talk", "2026-02-30", "10:00", "11:00", "Hall", "10")
      + new_event("X", "Talk", "2026-12-10", "25:00", "11:00", "Hall", "10")
      + new_event("X", "Talk", "2026-12-10", "11:00", "10:00", "Hall", "10")
      + new_event("X", "Talk", "2026-12-10", "10:00", "11:00", "Hall", "0")
      + new_event("X", "Talk", "2026-12-10", "10:00", "11:00", "Hall", "abc")
      + ["0"]], s5),
    ("Registration", "Normal",
     "Register a student for an open event with seats left",
     "E003, S26CSEU1374, Advika Chamoli, advika@example.edu",
     "Registered; seats left drops 60 -> 59",
     [register("E003", "S26CSEU1374", "Advika Chamoli", "advika@example.edu")
      + ["0"]], s6),
    ("Registration", "Invalid",
     "Same student ID registers twice for the same event",
     "E001, S26CSEU1001 (already registered)",
     "Rejected as duplicate",
     [register("E001", "s26cseu1001", "Aarav Mehta", "aarav.mehta@example.edu")
      + ["0"]], s7),
    ("Registration", "Boundary",
     "Fill an event to capacity, then try one more registration",
     "New event with capacity 1; register two different students",
     "First accepted; second rejected as full",
     [new_event("Mini Meetup", "Talk", "2026-12-10", "10:00", "11:00", "Room 5", "1")
      + register("E004", "S1", "First Student", "first@example.edu")
      + register("E004", "S2", "Second Student", "second@example.edu")
      + ["0"]], s8),
    ("Registration", "Invalid",
     "Malformed email address",
     "E001, S26CSEU1999, Test User, not-an-email",
     "Rejected; nothing saved",
     [register("E001", "S26CSEU1999", "Test User", "not-an-email") + ["0"]], s9),
    ("Cancellation", "Normal",
     "Cancel an event that has a registration, then try to register for it",
     "Cancel E002 (y); then register for E002",
     "Status Cancelled, records kept, hidden from list, registration refused",
     [["4", "E002", "y", "1"] + register("E002", "S9", "Late Student", "late@example.edu")
      + ["0"]], s10),
    ("Menu input", "Invalid",
     "Non-numeric, out-of-range and empty menu choices",
     "abc, 9, (blank), 0",
     "Invalid option message each time; no crash",
     [["abc", "9", "", "0"]], s11),
    ("CSV persistence", "Normal",
     "Register a student, exit, start the program again and open the report",
     "Session 1: register + exit. Session 2: menu 5",
     "Registration still present after restart",
     [register("E003", "S26CSEU1374", "Advika Chamoli", "advika@example.edu") + ["0"],
      ["5", "0"]], s12),
]


def main():
    rows, transcript, failures = [], [], 0
    real_files = (cep.EVENTS_FILE, cep.REGS_FILE)
    for n, (feature, kind, desc, inp, expected, sessions, check) in enumerate(SCENARIOS, 1):
        with tempfile.TemporaryDirectory() as tmp:
            cep.EVENTS_FILE = Path(tmp) / "events.csv"
            cep.REGS_FILE = Path(tmp) / "registrations.csv"
            out = "".join(run_session(s) for s in sessions)
            ok, actual = check(out, cep.load_events(), cep.load_registrations())
        failures += not ok
        rows.append({"test_id": n, "feature": feature, "type": kind,
                     "scenario": desc, "input": inp, "expected": expected,
                     "actual": actual, "status": "Pass" if ok else "FAIL"})
        transcript.append(f"{'#' * 70}\nTEST {n}: {feature} ({kind}) - {desc}\n"
                          f"Result: {'PASS' if ok else 'FAIL'}\n{'#' * 70}\n{out}\n")
    cep.EVENTS_FILE, cep.REGS_FILE = real_files

    with open(HERE / "testing_plan.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    (HERE / "demo_transcript.txt").write_text("\n".join(transcript), encoding="utf-8")
    for r in rows:
        print(f"Test {r['test_id']:>2} {r['status']:<4} {r['feature']} ({r['type']})")
    print(f"\n{len(rows) - failures}/{len(rows)} scenarios passed.")


if __name__ == "__main__":
    main()
