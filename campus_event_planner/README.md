# Campus Event Planner
Course: Computational Thinking and Programming (2026CSAE100) · S-20 Batch 39

Menu-driven Python console app (standard library only) that manages campus events
and registrations in CSV files, blocks venue clashes / duplicate / over-capacity
registrations, and reports demand.

## Run
    python campus_event_planner.py        # the program
    python -m unittest -v                 # 17 automated tests
    python run_scenarios.py               # 12 interactive scenarios -> testing_plan.csv, demo_transcript.txt

## Files
| File | Purpose |
|---|---|
| campus_event_planner.py | Complete program |
| events.csv, registrations.csv | Data (recreated with fictional samples if deleted) |
| test_event_planner.py | Unit tests |
| run_scenarios.py | Runs the 12 test-plan scenarios on temporary data |
| testing_plan.csv | Scenario results (observed, not assumed) |
| demo_transcript.txt | Console output of every scenario, for screenshots |
