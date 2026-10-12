from models import AppModel


class ApplicationController:
    """Coordinates startup checks without exposing database services to views."""

    def __init__(self, model: AppModel | None = None):
        self.model = model or AppModel()

    def initialize(self) -> None:
        self.model.initialize_database()

    def needs_first_run_setup(self) -> bool:
        return not self.model.has_registered_employees()

    def health(self):
        return self.model.health()

    def shutdown(self) -> None:
        self.model.shutdown()
