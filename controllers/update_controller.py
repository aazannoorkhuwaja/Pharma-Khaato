"""Optional internet update metadata, separate from the business database."""


class UpdateController:
    @staticmethod
    def check(force=False):
        from core.version_service import check_update_status
        return check_update_status(force=force)

    @staticmethod
    def enabled():
        from core.counter_preferences import read
        try:
            return read().get('automatic_update_checks', True) is not False
        except (OSError, ValueError):
            return True

    @staticmethod
    def set_enabled(enabled):
        from core.counter_preferences import update
        return update({'automatic_update_checks': bool(enabled)})
