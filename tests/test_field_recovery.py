def test_owner_code_requires_password_and_is_single_use(seeded_shop):
    from core.auth_service import enroll_owner_recovery, recover_owner_access, login_user
    assert not enroll_owner_recovery("admin", "wrong")[0]
    ok, code = enroll_owner_recovery("admin", "secret123")
    assert ok
    assert not recover_owner_access("admin","wrong","New-pass-123")[0]
    assert recover_owner_access("admin",code,"New-pass-123")[0]
    assert not recover_owner_access("admin",code,"Again-pass-123")[0]
    assert not login_user("admin","secret123")
    assert login_user("admin","New-pass-123")
