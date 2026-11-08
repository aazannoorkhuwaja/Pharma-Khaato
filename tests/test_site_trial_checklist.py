"""Site pilot recorder must not fabricate physical acceptance results."""
from scripts.site_trial_checklist import (
    CASES, ALLOWED, default_record, load, atomic_write, evaluate,
)


def test_site_trial_starts_all_cases_unverified(tmp_path):
    record = default_record()
    assert len(CASES) == 34
    assert ALLOWED == {"pass", "fail", "not_run", "blocked"}
    assert all(case["status"] == "not_run" for case in record["cases"].values())
    assert evaluate(record) == 2

    path = tmp_path / "trial.json"
    atomic_write(path, record)
    assert load(path)["cases"] == record["cases"]


def test_site_trial_does_not_approve_missing_or_blocked_check(tmp_path):
    record = default_record()
    for item in record["cases"].values():
        item["status"] = "pass"
    record["cases"]["printer_58"]["status"] = "blocked"
    assert evaluate(record) == 2
    record["cases"]["printer_58"]["status"] = "pass"
    assert evaluate(record) == 0
