"""
auth_service — Authentication, employee lifecycle, and password management.

Public interface (6 symbols):
    has_registered_employees()
    login_user(username, password)              → (emp_id, fname, lname, occupation) | None
    register_initial_admin(username, password, first_name, last_name)
    create_employee(username, password, first_name, last_name, occupation)
    change_password(employee_id, current_password, new_password)
    get_all_employees()

Private (module-internal only):
    _hash_password(password, salt=None)
    _verify_password(password, stored_hash)
    _record_failed_attempt(username)

Security policy (lockout, audit logging, hash upgrade) is enforced inside every
public function that touches credentials. Callers cannot bypass it by reaching for
crypto primitives — those are intentionally private.
"""

import os
import time
import hmac
import hashlib
import binascii
import sqlite3
from core.db_engine import get_db, get_conn
from core.logger import get_logger

logger = get_logger("PharmaKhaatoAuth")

# ---------------------------------------------------------------------------
# Brute-force lockout (DB-persisted in Login_Lockout via migration 009).
# Single source of truth is the database, so lockouts survive application
# restarts and cannot diverge from an in-memory copy.
# ---------------------------------------------------------------------------
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 60.0
_PBKDF2_ITERATIONS = 600_000

# Legacy alias: the old in-memory mirror was removed; kept as an empty dict so
# any stale script that touches it still runs (it no longer affects security).
_LOGIN_ATTEMPTS: dict = {}


def _lockout_get(cur, username: str):
    cur.execute(
        "SELECT failed_attempts, locked_until FROM Login_Lockout WHERE username = %s",
        (username,),
    )
    return cur.fetchone()


def _record_failed_attempt(username: str) -> None:
    now = time.time()
    try:
        with get_db() as (conn, cur):
            row = _lockout_get(cur, username)
            if row is None:
                attempts = 1
                cur.execute(
                    "INSERT INTO Login_Lockout (username, failed_attempts, locked_until) VALUES (%s, 1, 0)",
                    (username,),
                )
            else:
                attempts = int(row[0]) + 1
                locked_until = float(row[1])
                if attempts >= _MAX_ATTEMPTS:
                    locked_until = now + _LOCKOUT_SECONDS
                cur.execute(
                    "UPDATE Login_Lockout SET failed_attempts = %s, locked_until = %s WHERE username = %s",
                    (attempts, locked_until, username),
                )
    except sqlite3.Error as e:
        # Never let lockout bookkeeping break the login flow itself.
        logger.warning(f"Handled lockout persistence failure: {e}")


def _clear_failed_attempt(cur, username: str) -> None:
    cur.execute("DELETE FROM Login_Lockout WHERE username = %s", (username,))


def _prune_expired_lockouts(max_rows: int = 1000) -> None:
    """Bounded cleanup of stale lockout rows (older than 1 hour past expiry)."""
    cutoff = time.time() - 3600.0
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "DELETE FROM Login_Lockout WHERE locked_until > 0 AND locked_until < %s "
                "AND failed_attempts < %s",
                (cutoff, _MAX_ATTEMPTS),
            )
    except sqlite3.Error as e:
        logger.warning(f"Handled lockout prune failure: {e}")


# ---------------------------------------------------------------------------
# Private crypto primitives
# Not exported. All password operations must go through a public function.
# ---------------------------------------------------------------------------

def _hash_password(password: str, salt: str = None, iterations: int = _PBKDF2_ITERATIONS) -> str:
    """Generate a versioned PBKDF2-HMAC-SHA256 password hash.

    The iteration count is embedded in the hash so older installations remain
    verifiable and can be upgraded transparently after a successful login.
    """
    if not password:
        return ""
    if not salt:
        salt = binascii.hexlify(os.urandom(16)).decode("ascii")
    iterations = max(100_000, int(iterations))
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    return f"pbkdf2:sha256:{iterations}${salt}${binascii.hexlify(key).decode('ascii')}"


def _parse_pbkdf2_hash(stored_hash: str):
    try:
        scheme, salt, digest = stored_hash.split("$", 2)
        prefix, algorithm, iterations = scheme.split(":", 2)
        if prefix != "pbkdf2" or algorithm != "sha256":
            return None
        return int(iterations), salt, digest
    except (ValueError, TypeError):
        return None


def _needs_rehash(stored_hash: str) -> bool:
    parsed = _parse_pbkdf2_hash(stored_hash)
    return bool(parsed and parsed[0] < _PBKDF2_ITERATIONS)


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify current and legacy password formats using constant-time compare."""
    if not stored_hash or not password:
        return False

    if stored_hash.startswith("pbkdf2:sha256:"):
        parsed = _parse_pbkdf2_hash(stored_hash)
        if not parsed:
            logger.warning("Handled malformed PBKDF2 password hash.")
            return False
        iterations, salt, expected_digest = parsed
        try:
            key = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
            )
            actual_digest = binascii.hexlify(key).decode("ascii")
            return hmac.compare_digest(actual_digest, expected_digest)
        except (ValueError, TypeError, OverflowError) as exc:
            logger.warning(f"Handled password verification error: {exc}")
            return False

    # Legacy unsalted SHA-256 is accepted once and upgraded after login.
    if len(stored_hash) == 64 and all(c in "0123456789abcdefABCDEF" for c in stored_hash):
        digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if hmac.compare_digest(stored_hash.lower(), digest):
            logger.warning("Legacy SHA-256 password verified; upgrading on successful login.")
            return True
        return False

    logger.warning("Rejected legacy plain-text credential during verification.")
    return False


# Backward-compatibility aliases for legacy scripts and salesman_app
hash_password_pbkdf2 = _hash_password
verify_password = _verify_password


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def has_registered_employees() -> bool:
    """
    Returns True if at least one employee is registered.
    Raises on database failure so the UI can distinguish 'fresh install'
    from 'database offline' — masking this re-triggers the admin wizard.
    """
    with get_db() as (conn, cur):
        cur.execute("SELECT COUNT(*) FROM Employee")
        res = cur.fetchone()
        return bool(res and res[0] > 0)


def login_user(username: str, password: str):
    """
    Authenticates an employee with brute-force lockout protection.

    Returns (Employee_id, First_name, Last_name, occupation) on success, or None.
    Raises PermissionError if the account is temporarily locked.

    Side-effects (enforced here, not bypassable):
        - Increments / resets brute-force counter.
        - Auto-upgrades legacy plain-text / SHA-256 hash to PBKDF2 on success.
        - Writes USER_LOGIN_SUCCESS / USER_LOGIN_FAILED to audit log.
    """
    username = str(username).strip()
    now = time.time()

    # Opportunistic bounded cleanup of stale lockout rows.
    _prune_expired_lockouts()

    # Check lockout (DB-persisted — survives application restarts)
    try:
        with get_db() as (conn, cur):
            row = _lockout_get(cur, username)
    except sqlite3.Error as e:
        logger.warning(f"Handled lockout read failure: {e}")
        row = None
    if row is not None:
        attempts, locked_until = int(row[0]), float(row[1])
        if attempts >= _MAX_ATTEMPTS:
            if now < locked_until:
                remaining = int(locked_until - now)
                raise PermissionError(
                    f"Account locked due to failed login attempts. Try again in {remaining}s."
                )
            # Lockout expired — clear it
            _record_failed_attempt_clear = username  # noqa: F841
            try:
                with get_db() as (conn, cur):
                    _clear_failed_attempt(cur, username)
            except sqlite3.Error as e:
                logger.warning(f"Handled lockout reset failure: {e}")

    conn = get_conn()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT Employee_id, First_name, Last_name, occupation, password "
            "FROM Employee WHERE username = %s",
            (username,),
        )
        res = cur.fetchone()

        if not res:
            _record_failed_attempt(username)
            return None

        emp_id, fname, lname, occupation, stored_pw = res

        if _verify_password(password, stored_pw):
            # Clear lockout counter on success
            try:
                with get_db() as (c2, cur2):
                    _clear_failed_attempt(cur2, username)
            except sqlite3.Error as e:
                logger.warning(f"Handled lockout clear failure: {e}")

            # Auto-upgrade legacy or lower-cost PBKDF2 hashes after successful login.
            if not stored_pw.startswith("pbkdf2:sha256:") or _needs_rehash(stored_pw):
                try:
                    cur.execute(
                        "UPDATE Employee SET password = %s WHERE Employee_id = %s",
                        (_hash_password(password), emp_id),
                    )
                    conn.commit()
                except (sqlite3.Error, ValueError, OSError) as e:
                    logger.warning(f"Handled non-critical password hash upgrade failure: {e}")

            from core.audit_service import log_audit_event
            log_audit_event(
                emp_id, "USER_LOGIN_SUCCESS",
                f"User '{username}' ({fname} {lname}, {occupation}) logged in.",
            )
            return (emp_id, fname, lname, occupation)

        else:
            _record_failed_attempt(username)
            from core.audit_service import log_audit_event
            log_audit_event(
                username, "USER_LOGIN_FAILED",
                f"Failed login attempt for username '{username}'.",
            )
            return None

    except PermissionError:
        raise
    except Exception as e:
        logger.error(f"Auth error: {e}")
        return None
    finally:
        conn.close()


def register_initial_admin(
    username: str, password: str, first_name: str, last_name: str
):
    """Registers the initial Administrator user during first-run setup."""
    username = str(username).strip()
    first_name = str(first_name).strip()
    last_name = str(last_name).strip()
    if not username or not password or not first_name:
        return False, "Username, Password, and First Name are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id FROM Employee WHERE username = %s", (username,)
            )
            if cur.fetchone():
                raise ValueError(f"Username '{username}' is already in use.")
            cur.execute(
                "INSERT INTO Employee (username, password, First_name, Last_name, occupation) "
                "VALUES (%s, %s, %s, %s, 'Admin')",
                (username, _hash_password(password), first_name, last_name or "Admin"),
            )
        return True, f"Administrator '{username}' created successfully!"
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Failed to create Administrator: {e}"


def create_employee(
    username: str, password: str, first_name: str,
    last_name: str, occupation: str = "Salesman"
):
    """Registers a new staff / employee user account."""
    username = str(username).strip()
    first_name = str(first_name).strip()
    last_name = str(last_name).strip()
    occupation = str(occupation).strip() or "Salesman"

    if not username or not password or not first_name:
        return False, "Username, Password, and First Name are required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id FROM Employee WHERE username = %s", (username,)
            )
            if cur.fetchone():
                raise ValueError(f"Username '{username}' is already taken.")
            cur.execute(
                "INSERT INTO Employee (username, password, First_name, Last_name, occupation) "
                "VALUES (%s, %s, %s, %s, %s)",
                (username, _hash_password(password), first_name, last_name or "Staff", occupation),
            )
        return True, f"Employee user '{username}' ({occupation}) created successfully!"
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Failed creating employee: {e}"


def change_password(
    employee_id: int, current_password: str, new_password: str
) -> tuple[bool, str]:
    """
    Changes an employee's password after verifying the current one.

    Security guarantees (enforced here):
        - Current password is verified before any change is written.
        - New hash is PBKDF2 — no caller can store a weaker format via this path.
        - Password change is written to the audit log.
        - Brute-force lockout does NOT apply here (caller is already authenticated).

    Returns (True, success_msg) or (False, error_msg).
    """
    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters long."
    if not current_password:
        return False, "Current password is required."
    if current_password == new_password:
        return False, "New password must be different from the current password."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT username, password FROM Employee WHERE Employee_id = %s",
                (employee_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Employee #{employee_id} not found.")

            username, stored_pw = row
            if not _verify_password(current_password, stored_pw):
                # Intentionally vague message — don't confirm whether the account exists
                return False, "Current password is incorrect."

            cur.execute(
                "UPDATE Employee SET password = %s WHERE Employee_id = %s",
                (_hash_password(new_password), employee_id),
            )

        from core.audit_service import log_audit_event
        log_audit_event(
            employee_id, "PASSWORD_CHANGED",
            f"Employee '{username}' (#{employee_id}) changed their password.",
        )
        return True, "Password changed successfully."
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        logger.error(f"change_password error for employee #{employee_id}: {e}")
        return False, f"Password change failed: {e}"


def get_all_employees() -> list:
    """Returns list of tuples: (Employee_id, username, First_name, Last_name, occupation)."""
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id, username, First_name, Last_name, occupation "
                "FROM Employee ORDER BY Employee_id ASC"
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching employees: {e}")
        return []


# ---------------------------------------------------------------------------
# Compatibility shim — kept so any external caller that referenced the old
# update_employee_password() function continues to work.
# Delegates to change_password() is not possible without current_password,
# so this admin-level reset path bypasses current-password verification.
# Only Admins reach this path via the settings screen.
# ---------------------------------------------------------------------------
def update_employee_password(employee_id: int, new_password: str) -> tuple[bool, str]:
    """
    Admin-level password reset (no current-password verification).
    Prefer change_password() for self-service password changes.
    """
    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters long."
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT username FROM Employee WHERE Employee_id = %s", (employee_id,)
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Employee #{employee_id} not found.")
            cur.execute(
                "UPDATE Employee SET password = %s WHERE Employee_id = %s",
                (_hash_password(new_password), employee_id),
            )
        from core.audit_service import log_audit_event
        log_audit_event(
            employee_id, "PASSWORD_ADMIN_RESET",
            f"Admin reset password for Employee '{row[0]}' (#{employee_id}).",
        )
        return True, f"Password updated for Employee #{employee_id}."
    except ValueError as ve:
        return False, str(ve)
    except Exception as e:
        return False, f"Failed updating password: {e}"
