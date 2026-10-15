"""UI-facing navigation cache controller.

Keeps Qt/router code behind the MVC boundary while delegating revision state to
core infrastructure.
"""

from core.data_revision import snapshot


class NavigationController:
    @staticmethod
    def revision_snapshot(domains):
        return snapshot(domains)
