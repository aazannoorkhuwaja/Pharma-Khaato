"""Release approval requires human-attested evidence on exact candidate."""
from scripts.release_acceptance_gate import validate
from scripts.site_trial_checklist import default_record, CASES, load, atomic_write

SHA = "a" * 40
VERSION = "2.4.2"


def accepted_record():
    record = default_record()
    record.update(
        application_commit=SHA,
        application_version=VERSION,
        site="practice-shop-01",
        target_hardware="Windows 11, scanner X, printer Y",
        operator="test-operator",
        reviewer="shop-owner",
        approval={
            "decision": "approve_pilot",
            "date": "2026-11-09",
            "supervisor_signature_reference": "local-signed-sheet.pdf",
            "legal_tax_review_reference": "legal-review.txt",
        },
    )
    for name, _ in CASES:
        record["cases"][name]["status"] = "pass"
        record["cases"][name]["evidence"] = name + "-safe-evidence.txt"
    return record


def test_default_site_acceptance_is_blocked():
    errors = validate(default_record(), SHA, VERSION)
    assert errors and any("Site case not passed" in msg for msg in errors)
    assert any("supervised pilot approval" in msg for msg in errors)


def test_full_attested_record_is_structurally_complete():
    assert validate(accepted_record(), SHA, VERSION) == []


def test_mismatched_version_revision_block_release():
    r = accepted_record()
    assert any("revision" in x.lower() for x in validate(r, "b" * 40, VERSION))
    assert any("version" in x.lower() for x in validate(r, SHA, "2.5.0"))


def test_missing_backup_restore_hardware_evidence_blocks():
    r = accepted_record()
    r["cases"]["restore"]["evidence"] = ""
    assert any("restore" in x for x in validate(r, SHA, VERSION))
    r["cases"]["printer_58"]["status"] = "blocked"
    assert any("printer_58" in x for x in validate(r, SHA, VERSION))


def test_missing_supervisor_signoff_blocks():
    r = accepted_record()
    r["approval"]["supervisor_signature_reference"] = ""
    assert any("supervisor_signature_reference" in x for x in validate(r, SHA, VERSION))


def test_worksheet_roundtrip(tmp_path):
    path = tmp_path / "acceptance.json"
    atomic_write(path, accepted_record())
    assert validate(load(path), SHA, VERSION) == []
