from models import AppModel


class ApplicationController:
    """Coordinates startup checks and background app services for the UI shell."""

    def __init__(self, model: AppModel | None = None):
        self.model = model or AppModel()

    def initialize(self) -> None:
        self.model.initialize_database()

    def needs_first_run_setup(self) -> bool:
        return not self.model.has_registered_employees()

    def health(self):
        return self.model.health()

    def ensure_daily_backup(self, retention: int = 14):
        """Create the once-per-day safety backup without exposing core services to views."""
        from core.backup_service import ensure_daily_backup

        return ensure_daily_backup(retention=retention)

    def shutdown(self) -> None:
        self.model.shutdown()
