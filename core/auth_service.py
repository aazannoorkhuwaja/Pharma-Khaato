"""Authentication, staff accounts, password hashing, and login lockout."""

import os
import time
import hmac
import hashlib
import binascii
import sqlite3

from core.db_engine import get_db, get_conn
from core.logger import get_logger

logger = get_logger("PharmaKhaatoAuth")

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 60.0
_PBKDF2_ITERATIONS = 600_000
MIN_PASSWORD_LENGTH = 8

# Legacy compatibility only. Lockout state now lives exclusively in SQLite.
_LOGIN_ATTEMPTS: dict = {}


def validate_new_password(password: str) -> tuple[bool, str]:
    """Single password policy used by every account-creation/reset path.

    Pharma-Khaato deliberately avoids arbitrary complexity requirements. A
    minimum length is easier for staff to understand and permits memorable
    passphrases while still blocking very short credentials.
    """
    if not password:
        return False, "Enter a password."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Use at least {MIN_PASSWORD_LENGTH} characters for the password."
    return True, ""


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
                    "INSERT INTO Login_Lockout (username, failed_attempts, locked_until) "
                    "VALUES (%s, 1, 0)",
                    (username,),
                )
            else:
                attempts = int(row[0]) + 1
                locked_until = float(row[1])
                if attempts >= _MAX_ATTEMPTS:
                    locked_until = now + _LOCKOUT_SECONDS
                cur.execute(
                    "UPDATE Login_Lockout SET failed_attempts = %s, locked_until = %s "
                    "WHERE username = %s",
                    (attempts, locked_until, username),
                )
    except sqlite3.Error as exc:
        logger.warning(f"Handled lockout persistence failure: {exc}")


def _clear_failed_attempt(cur, username: str) -> None:
    cur.execute("DELETE FROM Login_Lockout WHERE username = %s", (username,))


def _prune_expired_lockouts() -> None:
    """Remove abandoned lockout rows well after they have expired."""
    cutoff = time.time() - 3600.0
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "DELETE FROM Login_Lockout WHERE locked_until > 0 AND locked_until < %s",
                (cutoff,),
            )
    except sqlite3.Error as exc:
        logger.warning(f"Handled lockout prune failure: {exc}")


def _hash_password(
    password: str,
    salt: str = None,
    iterations: int = _PBKDF2_ITERATIONS,
) -> str:
    """Generate a versioned PBKDF2-HMAC-SHA256 password hash."""
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
    """Verify current and legacy hashed credential formats."""
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


# Compatibility aliases used by older scripts.
hash_password_pbkdf2 = _hash_password
verify_password = _verify_password


def has_registered_employees() -> bool:
    """Return whether at least one employee exists; database errors propagate."""
    with get_db() as (conn, cur):
        cur.execute("SELECT COUNT(*) FROM Employee")
        row = cur.fetchone()
        return bool(row and row[0] > 0)


def login_user(username: str, password: str):
    """Authenticate an employee with persistent brute-force lockout protection."""
    username = str(username).strip()
    now = time.time()
    _prune_expired_lockouts()

    try:
        with get_db() as (conn, cur):
            row = _lockout_get(cur, username)
    except sqlite3.Error as exc:
        logger.warning(f"Handled lockout read failure: {exc}")
        row = None

    if row is not None:
        attempts, locked_until = int(row[0]), float(row[1])
        if attempts >= _MAX_ATTEMPTS:
            if now < locked_until:
                remaining = max(1, int(locked_until - now))
                raise PermissionError(
                    f"Too many failed sign-in attempts. Try again in {remaining} seconds."
                )
            try:
                with get_db() as (conn, cur):
                    _clear_failed_attempt(cur, username)
            except sqlite3.Error as exc:
                logger.warning(f"Handled lockout reset failure: {exc}")

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
        if not _verify_password(password, stored_pw):
            _record_failed_attempt(username)
            from core.audit_service import log_audit_event
            log_audit_event(
                username,
                "USER_LOGIN_FAILED",
                f"Failed login attempt for username '{username}'.",
            )
            return None

        try:
            with get_db() as (conn2, cur2):
                _clear_failed_attempt(cur2, username)
        except sqlite3.Error as exc:
            logger.warning(f"Handled lockout clear failure: {exc}")

        if not stored_pw.startswith("pbkdf2:sha256:") or _needs_rehash(stored_pw):
            try:
                cur.execute(
                    "UPDATE Employee SET password = %s WHERE Employee_id = %s",
                    (_hash_password(password), emp_id),
                )
                conn.commit()
            except (sqlite3.Error, ValueError, OSError) as exc:
                logger.warning(f"Handled password hash upgrade failure: {exc}")

        from core.audit_service import log_audit_event
        log_audit_event(
            emp_id,
            "USER_LOGIN_SUCCESS",
            f"User '{username}' ({fname} {lname}, {occupation}) logged in.",
        )
        return emp_id, fname, lname, occupation

    except PermissionError:
        raise
    except Exception as exc:
        logger.error(f"Authentication error: {exc}")
        return None
    finally:
        conn.close()


def register_initial_admin(
    username: str,
    password: str,
    first_name: str,
    last_name: str,
):
    """Register the first Administrator during initial setup."""
    username = str(username).strip()
    first_name = str(first_name).strip()
    last_name = str(last_name).strip()

    if not username or not first_name:
        return False, "Enter a username and first name."
    valid, message = validate_new_password(password)
    if not valid:
        return False, message

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id FROM Employee WHERE username = %s",
                (username,),
            )
            if cur.fetchone():
                return False, "That username is already in use."
            cur.execute(
                "INSERT INTO Employee (username, password, First_name, Last_name, occupation) "
                "VALUES (%s, %s, %s, %s, 'Admin')",
                (username, _hash_password(password), first_name, last_name or "Admin"),
            )
        return True, "Administrator account created."
    except Exception as exc:
        logger.error(f"Initial administrator creation failed: {exc}")
        return False, "The administrator account could not be created. Please try again."


def create_employee(
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    occupation: str = "Salesman",
):
    """Register a new staff account."""
    username = str(username).strip()
    first_name = str(first_name).strip()
    last_name = str(last_name).strip()
    occupation = str(occupation).strip() or "Salesman"

    if not username or not first_name:
        return False, "Enter a username and first name."
    valid, message = validate_new_password(password)
    if not valid:
        return False, message

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id FROM Employee WHERE username = %s",
                (username,),
            )
            if cur.fetchone():
                return False, "That username is already in use."
            cur.execute(
                "INSERT INTO Employee (username, password, First_name, Last_name, occupation) "
                "VALUES (%s, %s, %s, %s, %s)",
                (
                    username,
                    _hash_password(password),
                    first_name,
                    last_name or "Staff",
                    occupation,
                ),
            )
        return True, f"Staff account '{username}' created."
    except Exception as exc:
        logger.error(f"Staff account creation failed: {exc}")
        return False, "The staff account could not be created. Please try again."


def change_password(
    employee_id: int,
    current_password: str,
    new_password: str,
) -> tuple[bool, str]:
    """Change a staff member's own password after current-password verification."""
    valid, message = validate_new_password(new_password)
    if not valid:
        return False, message
    if not current_password:
        return False, "Enter your current password."
    if current_password == new_password:
        return False, "Choose a password different from your current password."

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT username, password FROM Employee WHERE Employee_id = %s",
                (employee_id,),
            )
            row = cur.fetchone()
            if not row:
                return False, "This staff account could not be found."

            username, stored_pw = row
            if not _verify_password(current_password, stored_pw):
                return False, "Current password is incorrect."

            cur.execute(
                "UPDATE Employee SET password = %s WHERE Employee_id = %s",
                (_hash_password(new_password), employee_id),
            )

        from core.audit_service import log_audit_event
        log_audit_event(
            employee_id,
            "PASSWORD_CHANGED",
            f"Employee '{username}' changed their password.",
        )
        return True, "Password changed."
    except Exception as exc:
        logger.error(f"Password change failed for employee {employee_id}: {exc}")
        return False, "Password could not be changed. Please try again."


def get_all_employees() -> list:
    """Return (Employee_id, username, First_name, Last_name, occupation) rows."""
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT Employee_id, username, First_name, Last_name, occupation "
                "FROM Employee ORDER BY Employee_id ASC"
            )
            return cur.fetchall()
    except Exception as exc:
        logger.error(f"Error fetching employees: {exc}")
        return []


def update_employee_password(employee_id: int, new_password: str) -> tuple[bool, str]:
    """Administrator-level password reset without current-password verification."""
    valid, message = validate_new_password(new_password)
    if not valid:
        return False, message

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT username FROM Employee WHERE Employee_id = %s",
                (employee_id,),
            )
            row = cur.fetchone()
            if not row:
                return False, "This staff account could not be found."
            username = row[0]
            cur.execute(
                "UPDATE Employee SET password = %s WHERE Employee_id = %s",
                (_hash_password(new_password), employee_id),
            )

        from core.audit_service import log_audit_event
        log_audit_event(
            employee_id,
            "PASSWORD_ADMIN_RESET",
            f"Administrator reset password for employee '{username}'.",
        )
        return True, f"Password reset for {username}."
    except Exception as exc:
        logger.error(f"Administrator password reset failed for employee {employee_id}: {exc}")
        return False, "Password could not be reset. Please try again."
