"""Exercise startup decisions and owner setup against a real isolated database."""
from PySide6.QtWidgets import QDialog


def test_fresh_startup_requires_setup_before_sign_in(qapp, fresh_db, monkeypatch):
    from ui.app import application
    from controllers.application_controller import ApplicationController
    events = []
    class Setup:
        Accepted = QDialog.Accepted
        def exec(self):
            assert ApplicationController().needs_first_run_setup()
            events.append('setup')
            # Closing setup must never fall through to an unusable login screen.
            return QDialog.Rejected
    class Login:
        def __init__(self):
            raise AssertionError('Sign-in was shown before owner setup completed')
    monkeypatch.setattr(application, 'FirstRunWizardDialog', Setup)
    monkeypatch.setattr(application, 'LoginDialog', Login)
    assert application.run_app() == 0
    assert events == ['setup']


def test_setup_form_creates_owner_and_the_chosen_password_works(qapp, fresh_db):
    from controllers.application_controller import ApplicationController
    from controllers.auth_controller import AuthController
    from ui.screens.first_run_wizard import FirstRunWizardDialog
    controller = ApplicationController()
    controller.initialize()
    assert controller.needs_first_run_setup()
    dialog = FirstRunWizardDialog(show_message_box=False)
    try:
        for field, value in [('txt_name','Practice Pharmacy'), ('txt_address','Practice Street'),
                             ('txt_phone','03000000000'), ('txt_fname','Owner'),
                             ('txt_user','my-owner'), ('txt_pass','ChosenPass-8472')]:
            getattr(dialog,field).setText(value)
        dialog.on_submit()
        assert dialog.result() == QDialog.Accepted
        assert not controller.needs_first_run_setup()
        assert AuthController().login('my-owner','ChosenPass-8472')
        assert not AuthController().login('admin','demo1234')
    finally:
        dialog.deleteLater()
        qapp.processEvents()


def test_existing_owner_goes_to_sign_in_without_replacing_account(qapp, seeded_shop, monkeypatch):
    from ui.app import application
    from controllers.auth_controller import AuthController
    events = []
    class Setup:
        def __init__(self):
            raise AssertionError('Existing owner must not be replaced by first-run setup')
    class Login:
        def exec(self):
            events.append('sign-in')
            return QDialog.Rejected
    monkeypatch.setattr(application,'FirstRunWizardDialog',Setup)
    monkeypatch.setattr(application,'LoginDialog',Login)
    monkeypatch.setattr(application.ApplicationController,'start_shop_service',staticmethod(lambda:None))
    assert application.run_app() == 0
    assert events == ['sign-in']
    assert AuthController().login('admin','secret123')


def test_completed_setup_reaches_sign_in_with_the_new_owner(qapp, fresh_db, monkeypatch):
    from ui.app import application
    from controllers.auth_controller import AuthController
    events = []
    def complete_setup(dialog):
        for name, value in [('txt_name','New Shop'), ('txt_address','Practice Street'),
                            ('txt_phone','03000000000'), ('txt_fname','Owner'),
                            ('txt_user','new-owner'), ('txt_pass','ChosenPass-8472')]:
            getattr(dialog,name).setText(value)
        dialog.on_submit()
        events.append('setup')
        return dialog.result()
    class Login:
        def __init__(self):
            from PySide6.QtWidgets import QLineEdit
            self.txt_username = QLineEdit()
            self.txt_password = QLineEdit()
        def exec(self):
            assert self.txt_username.text() == 'new-owner'
            assert self.txt_password.text() == ''
            assert AuthController().login('new-owner','ChosenPass-8472')
            events.append('sign-in')
            return QDialog.Rejected
    original = application.FirstRunWizardDialog
    monkeypatch.setattr(original,'exec',complete_setup)
    # Disable success toast only; creation and validation still use the real form.
    monkeypatch.setattr('ui.screens.first_run_wizard.show_toast',lambda *a,**k:None)
    monkeypatch.setattr(application,'LoginDialog',Login)
    monkeypatch.setattr(application.ApplicationController,'start_shop_service',staticmethod(lambda:None))
    assert application.run_app() == 0
    assert events == ['setup','sign-in']


def test_sign_in_help_explains_preserved_accounts_without_changing_them(qapp, seeded_shop, monkeypatch):
    from ui.screens import login_screen
    from controllers.auth_controller import AuthController
    notices = []
    monkeypatch.setattr(login_screen.QMessageBox,'information',lambda parent,title,text:notices.append(text))
    dialog = login_screen.LoginDialog()
    try:
        dialog.btn_sign_in_help.click()
        assert 'There is no default password.' in notices[0]
        assert 'Reinstalling keeps that account' in notices[0]
        assert AuthController().login('admin','secret123')
    finally:
        dialog.deleteLater()
        qapp.processEvents()
