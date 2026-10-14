"""Backward-compatible health checker routed through the MVC controller."""

from controllers.application_controller import ApplicationController


class SystemHealthChecker:
    @staticmethod
    def run_diagnostics():
        return ApplicationController().health()
