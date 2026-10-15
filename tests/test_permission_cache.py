"""Permission-cache regression coverage."""

from contextlib import contextmanager


def test_role_cache_does_not_cross_database_paths(monkeypatch, tmp_path):
    from core import permission_service

    state = {
        "path": str(tmp_path / "admin.sqlite"),
        "role": "Admin",
    }

    class Cursor:
        def execute(self, _sql, _params):
            return None

        def fetchone(self):
            return (state["role"],)

    @contextmanager
    def fake_get_db():
        yield None, Cursor()

    monkeypatch.setattr(permission_service, "get_db", fake_get_db)
    monkeypatch.setattr(
        permission_service.PathManager,
        "get_db_path",
        staticmethod(lambda: state["path"]),
    )
    permission_service.clear_permission_cache()

    assert permission_service.get_employee_role(1) == "admin"

    # A different database may legitimately reuse employee ID 1. It must not
    # inherit the first database's cached administrator role.
    state["path"] = str(tmp_path / "viewer.sqlite")
    state["role"] = "Viewer"
    assert permission_service.get_employee_role(1) == "viewer"
    assert not permission_service.has_permission(1, "pos.sell")

    permission_service.clear_permission_cache()
