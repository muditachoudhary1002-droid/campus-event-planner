"""Unit tests for Campus Event Planner.  Run:  python -m unittest -v"""
import tempfile
import unittest
from pathlib import Path

import campus_event_planner as cep

T = cep.parse_time


def make_event(eid="E001", venue="Hall A", date="2026-12-05",
               start="10:00", end="12:00", cap="2", status="Open"):
    return {"event_id": eid, "title": "T", "category": "Workshop", "date": date,
            "start_time": start, "end_time": end, "venue": venue,
            "capacity": cap, "status": status}


# ---- The six tests listed in the report ------------------------------------
class ReportTests(unittest.TestCase):
    def test_overlapping_intervals(self):
        events = [make_event()]
        self.assertIsNotNone(
            cep.find_venue_conflict(events, "Hall A", "2026-12-05", "11:00", "13:00"))

    def test_adjacent_intervals_allowed(self):
        events = [make_event(end="12:00")]
        self.assertIsNone(
            cep.find_venue_conflict(events, "Hall A", "2026-12-05", "12:00", "14:00"))

    def test_different_date_or_venue(self):
        events = [make_event()]
        self.assertIsNone(
            cep.find_venue_conflict(events, "Hall A", "2026-12-06", "10:00", "12:00"))
        self.assertIsNone(
            cep.find_venue_conflict(events, "Hall B", "2026-12-05", "10:00", "12:00"))

    def test_cancelled_event_ignored(self):
        events = [make_event(status="Cancelled")]
        self.assertIsNone(
            cep.find_venue_conflict(events, "Hall A", "2026-12-05", "10:00", "12:00"))

    def test_email_shape(self):
        for good in ("a@b.com", "first.last@college.edu"):
            self.assertTrue(cep.is_valid_email(good), good)
        for bad in ("", "abc", "a@b", "@b.com", "a@@b.com", "a b@c.com", "a@.com"):
            self.assertFalse(cep.is_valid_email(bad), bad)

    def test_sequential_ids(self):
        rows = [{"event_id": "E003"}, {"event_id": "E010"}, {"event_id": "E007"}]
        self.assertEqual(cep.next_id(rows, "event_id", "E"), "E011")
        self.assertEqual(cep.next_id([], "event_id", "E"), "E001")


# ---- Extra tests for the checks marked "pending" in the report --------------
class RuleTests(unittest.TestCase):
    def test_venue_compare_is_case_insensitive(self):
        events = [make_event(venue="Hall A")]
        self.assertIsNotNone(
            cep.find_venue_conflict(events, "hall a", "2026-12-05", "10:30", "11:00"))

    def test_build_event_rejects_bad_input(self):
        ev = []
        bad = [("2026-13-40", "10:00", "11:00", "10"),   # impossible date
               ("2026-12-05", "25:00", "11:00", "10"),   # impossible time
               ("2026-12-05", "11:00", "10:00", "10"),   # end before start
               ("2026-12-05", "10:00", "11:00", "0"),    # zero capacity
               ("2026-12-05", "10:00", "11:00", "-5"),   # negative capacity
               ("2026-12-05", "10:00", "11:00", "abc")]  # not a number
        for date, s, e, cap in bad:
            event, err = cep.build_event(ev, "X", "Talk", date, s, e, "Hall", cap)
            self.assertIsNone(event)
            self.assertTrue(err)

    def test_build_event_success_and_conflict(self):
        ev = [make_event()]
        event, err = cep.build_event(ev, "New", "talk", "2026-12-05",
                                     "12:00", "13:00", "Hall A", "30")
        self.assertIsNone(err)
        self.assertEqual(event["event_id"], "E002")
        self.assertEqual(event["category"], "Talk")
        event, err = cep.build_event(ev, "New", "talk", "2026-12-05",
                                     "11:00", "13:00", "Hall A", "30")
        self.assertIsNone(event)
        self.assertIn("conflict", err.lower())

    def test_registration_rules(self):
        events = [make_event(cap="2")]
        regs = []

        def reg(sid, email="s@x.edu", eid="E001"):
            row, err = cep.build_registration(events, regs, eid, sid, "Name", email)
            if row:
                regs.append(row)
            return row, err

        self.assertIsNone(reg("S1")[1])
        self.assertIn("already registered", reg("s1")[1])   # duplicate, any case
        self.assertIn("invalid", reg("S2", email="bad")[1])
        self.assertIsNone(reg("S2")[1])
        self.assertIn("full", reg("S3")[1])                 # capacity reached
        self.assertIn("No event", reg("S3", eid="E999")[1])

    def test_cancelled_event_blocks_registration(self):
        events = [make_event(status="Cancelled")]
        row, err = cep.build_registration(events, [], "E001", "S1", "N", "a@b.com")
        self.assertIsNone(row)
        self.assertIn("Cancelled", err)

    def test_demand_summary_sample_data(self):
        events, regs = cep.SAMPLE_EVENTS, cep.SAMPLE_REGS
        ranking, cats, total, cap = cep.demand_summary(events, regs)
        self.assertEqual((total, cap), (3, 180))
        self.assertEqual([r["event"]["event_id"] for r in ranking],
                         ["E001", "E002", "E003"])
        self.assertAlmostEqual(total / cap * 100, 1.67, places=1)
        self.assertEqual(cats, {"Workshop": 2, "Cultural": 1, "Seminar": 0})

    def test_demand_tie_break_and_cancelled_excluded(self):
        events = [make_event("E001", cap="10"), make_event("E002", cap="20"),
                  make_event("E003", cap="10", status="Cancelled")]
        regs = [{"event_id": "E001"}] * 5 + [{"event_id": "E002"}] * 10 \
            + [{"event_id": "E003"}] * 9
        ranking, _, total, cap = cep.demand_summary(events, regs)
        # both 50%: E002 has more registrations so it ranks first
        self.assertEqual([r["event"]["event_id"] for r in ranking], ["E002", "E001"])
        self.assertEqual((total, cap), (15, 30))      # cancelled E003 excluded

    def test_guidance_thresholds(self):
        self.assertEqual(cep.demand_guidance(0.75), "High demand")
        self.assertEqual(cep.demand_guidance(0.74), "Filling")
        self.assertEqual(cep.demand_guidance(0.40), "Filling")
        self.assertEqual(cep.demand_guidance(0.39), "More promotion may help")


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = (cep.EVENTS_FILE, cep.REGS_FILE)
        cep.EVENTS_FILE = Path(self.tmp.name) / "events.csv"
        cep.REGS_FILE = Path(self.tmp.name) / "registrations.csv"

    def tearDown(self):
        cep.EVENTS_FILE, cep.REGS_FILE = self.old
        self.tmp.cleanup()

    def test_files_created_with_sample_data(self):
        cep.ensure_files()
        self.assertEqual(len(cep.load_events()), 3)
        self.assertEqual(len(cep.load_registrations()), 3)

    def test_data_survives_reload(self):
        cep.ensure_files()
        events = cep.load_events()
        events[0]["status"] = cep.CANCELLED
        cep.save_csv(cep.EVENTS_FILE, cep.EVENT_FIELDS, events)
        self.assertEqual(cep.load_events()[0]["status"], "Cancelled")
        self.assertEqual(len(cep.load_registrations()), 3)   # history kept

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(cep.load_events(), [])


if __name__ == "__main__":
    unittest.main()
