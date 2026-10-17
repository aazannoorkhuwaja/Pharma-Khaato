from models import AppModel


class ApplicationController:
    """Coordinates startup checks and background app services for the UI shell."""

    def __init__(self, model: AppModel | None = None):
        self.model = model or AppModel()

    def initialize(self) -> None:
        self.model.initialize_database()

    @staticmethod
    def is_remote():
        from core.lan_config import load_counter_config
        return bool(load_counter_config())

    def needs_first_run_setup(self) -> bool:
        return not self.model.has_registered_employees()

    def health(self):
        return self.model.health()

    def single_instance_lock_path(self) -> str:
        """Return the per-data-directory desktop lock path through the MVC boundary."""
        from pathlib import Path
        from core.path_manager import PathManager

        return str(Path(PathManager.get_config_dir()) / "application.lock")

    def ensure_daily_backup(self, retention: int = 14):
        """Create the once-per-day safety backup without exposing core services to views."""
        if hasattr(self.model, "ensure_daily_backup"):
            return self.model.ensure_daily_backup(retention=retention)
        from core.backup_service import ensure_daily_backup
        return ensure_daily_backup(retention=retention)

    @staticmethod
    def worker_thread_limit():
        from core.db_engine import bounded_setting
        return bounded_setting("PHARMA_KHAATO_WORKER_THREADS", 2, 1, 4)

    @staticmethod
    def start_shop_service():
        from core.lan_config import start_configured_shop_server
        return start_configured_shop_server()

    @staticmethod
    def sign_out():
        from core.lan_config import enabled_counter_client
        client = enabled_counter_client()
        if client is not None:
            client.logout()

    def shutdown(self) -> None:
        self.model.shutdown()

    @staticmethod
    def recovery_backups():
        from core.backup_service import list_backups
        return list_backups()

    @staticmethod
    def recover_from_backup(filepath, username, password):
        from core.recovery_service import recover_from_backup
        return recover_from_backup(filepath, username, password)
