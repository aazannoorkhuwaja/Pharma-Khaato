"""Installed recovery interaction stays responsive and never overwrites a shop."""
import threading


def test_recovery_validation_does_not_start_work(qtbot, monkeypatch):
    from ui.dialogs import recovery_bundle_dialog as module
    calls = []
    monkeypatch.setattr(module, 'perform_recovery', lambda *args: calls.append(args))
    dialog = module.RecoveryBundleDialog()
    qtbot.addWidget(dialog)
    dialog.start()
    assert not dialog.busy and not calls
    assert 'Choose source' in dialog.status.text()


def test_recovery_busy_state_and_success_require_close(qtbot, monkeypatch):
    from ui.dialogs import recovery_bundle_dialog as module
    entered, release = threading.Event(), threading.Event()
    def operation(*args):
        entered.set()
        assert release.wait(5)
        return '/fixture/new-shop'
    monkeypatch.setattr(module, 'perform_recovery', operation)
    dialog = module.RecoveryBundleDialog()
    qtbot.addWidget(dialog)
    dialog.mode.setCurrentIndex(1)
    dialog.source.setText('/fixture/backup.pkrecovery')
    dialog.destination.setText('/fixture/new-shop')
    dialog.passphrase.setText('correct recovery passphrase')
    dialog.show()
    try:
        dialog.start()
        qtbot.waitUntil(entered.is_set)
        assert dialog.busy and not dialog.run_button.isEnabled()
        assert not dialog.passphrase.text()
        dialog.reject()
        assert dialog.isVisible()
        release.set()
        qtbot.waitUntil(lambda: not dialog.busy)
        assert dialog.completed and not dialog.run_button.isEnabled()
        assert 'Completed:' in dialog.status.text()
    finally:
        release.set()
        qtbot.waitUntil(lambda: not dialog.tasks._active)
        dialog.close()


def test_recovery_rejects_missing_shop_before_creating_data(tmp_path):
    import pytest
    from ui.dialogs.recovery_bundle_dialog import perform_recovery
    missing = tmp_path / 'not-a-shop'
    with pytest.raises(ValueError, match='no pharmacy database'):
        perform_recovery('export', str(missing), str(tmp_path/'export'), 'owner', 'pw', 'sixteen-character-passphrase')
    assert not missing.exists()
