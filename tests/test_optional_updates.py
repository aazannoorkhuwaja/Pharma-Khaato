"""Offline-first, release authenticity and non-disruptive update notices."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


def release(version='99.0.0', **changes):
    tag = 'v' + version
    name = f'Pharma-Khaato-{version}-Setup-Windows-x64.exe'
    return {'tag_name':tag, 'draft':False, 'prerelease':False, 'body':'Fixes stock counting and receipt layout.',
            'assets':[{'name':name}, {'name':name+'.sha256'}], **changes}


class Response:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, size):
        return json.dumps(self.value).encode()[:size]


def test_update_uses_installed_version_and_official_page(fresh_db, monkeypatch):
    from core import version_service as service
    from config import ApplicationSettings
    calls = []
    def request(req, timeout):
        calls.append(req)
        assert timeout == 3.0
        return Response(release(html_url='https://malicious.invalid/install.exe'))
    monkeypatch.setattr(service.urllib.request, 'urlopen', request)
    info = service.check_update_status()['update']
    assert info['current_version'] == ApplicationSettings.APP_VERSION
    assert info['release_notes'].startswith('Fixes stock')
    assert info['download_url'] == 'https://github.com/aazannoorkhuwaja/Pharma-Khaato/releases/tag/v99.0.0'
    assert calls[0].data is None
    assert service.check_update_status()['status'] == 'deferred'
    assert len(calls) == 1
    assert service.check_update_status(force=True)['status'] == 'available'


@pytest.mark.parametrize('tag', ['v99.0.0-beta', 'v99.0.0/evil', '99', 'v99.0.0<script>', ''])
def test_invalid_and_prerelease_tags_are_not_updates(tag):
    from core.version_service import _release_info
    assert _release_info(release(tag_name=tag)) is None


@pytest.mark.parametrize('changes', [{'draft':True}, {'prerelease':True}, {'assets':[]}])
def test_draft_or_incomplete_windows_release_is_not_offered(changes):
    from core.version_service import _release_info
    assert _release_info(release(**changes)) is None


def test_current_version_is_not_an_update():
    from config import ApplicationSettings
    from core.version_service import _release_info
    assert _release_info(release(ApplicationSettings.APP_VERSION)) is None


def test_offline_check_never_blocks_later_reconnection(fresh_db, monkeypatch):
    from core import version_service as service
    def offline(*args, **kwargs):
        raise OSError('No internet')
    monkeypatch.setattr(service.urllib.request, 'urlopen', offline)
    assert service.check_update_status() == {'status':'offline'}
    assert not service._state_path().exists()
    monkeypatch.setattr(service.urllib.request, 'urlopen', lambda *a, **k:Response(release()))
    assert service.check_update_status()['status'] == 'available'
    assert service._state_path().exists()


def test_oversized_response_is_ignored(fresh_db, monkeypatch):
    from core import version_service as service
    monkeypatch.setattr(service, 'MAX_RESPONSE_BYTES', 20)
    monkeypatch.setattr(service.urllib.request, 'urlopen', lambda *a, **k:Response(release()))
    assert service.check_update_status()['status'] == 'offline'


def test_update_notice_waits_for_cart_and_pending_checkout(qapp, fresh_db, monkeypatch):
    from ui.dialogs import update_dialog as ui
    from ui.app.state.session_state import SessionState
    from PySide6.QtWidgets import QWidget
    from core.version_service import _release_info
    window = QWidget()
    window.current_user = {'id':1}
    window.show()
    notifier = ui.UpdateNotifier(window)
    state = SessionState.get_instance()
    previous = state.active_cart, state.pending_checkout
    created = []
    class Dialog:
        def __init__(self, info, parent):
            created.append(info)
        def setModal(self, value):
            pass
        def show(self):
            pass
        def isVisible(self):
            return True
    monkeypatch.setattr(ui, 'UpdateDialog', Dialog)
    try:
        state.active_cart = [{'name':'Medicine'}]
        state.pending_checkout = None
        notifier.pending = _release_info(release())
        notifier.offer()
        assert not created
        state.active_cart = []
        state.pending_checkout = {'token':'pending'}
        notifier.offer()
        assert not created
        state.pending_checkout = None
        notifier.offer()
        assert len(created) == 1 and notifier.pending is None
        assert not notifier.timer.isActive()  # headless smoke never phones home
    finally:
        state.active_cart, state.pending_checkout = previous
        window.close()


def test_notes_are_plain_text_and_later_does_not_open_browser(qapp, fresh_db, monkeypatch):
    from ui.dialogs import update_dialog as ui
    from core.version_service import _release_info
    info = _release_info(release(body='<script>evil()</script> Fixes stock.'))
    opened = Mock(return_value=True)
    monkeypatch.setattr(ui.QDesktopServices, 'openUrl', opened)
    dialog = ui.UpdateDialog(info)
    assert dialog.notes.toPlainText() == info['release_notes']
    dialog.reject()
    opened.assert_not_called()
    dialog.download(info['download_url'])
    opened.assert_called_once()


def test_automatic_checks_can_be_disabled_and_manual_check_still_works(qapp, fresh_db, monkeypatch):
    from controllers.update_controller import UpdateController
    from ui.dialogs.update_dialog import UpdateNotifier
    from PySide6.QtWidgets import QWidget
    assert UpdateController.set_enabled(False)
    assert not UpdateController.enabled()
    window = QWidget()
    window.current_user = {'id':1}
    notifier = UpdateNotifier(window)
    submitted = []
    notifier.tasks = SimpleNamespace(run=lambda *args:submitted.append(args))
    notifier.poll()
    assert not submitted
    notifier.poll(manual=True)
    assert len(submitted) == 1
    window.close()


def test_about_dialog_names_match_license(qapp, fresh_db):
    from config import ApplicationSettings
    from ui.dialogs.about_dialog import AboutDialog
    from PySide6.QtWidgets import QLabel
    from pathlib import Path
    license_text = (Path(__file__).resolve().parents[1] / 'LICENSE').read_text()
    dialog = AboutDialog(SimpleNamespace(poll=lambda **kwargs:None))
    text = ' '.join(label.text() for label in dialog.findChildren(QLabel))
    for builder in ApplicationSettings.BUILDERS:
        assert builder in license_text and builder in text
    dialog.close()
