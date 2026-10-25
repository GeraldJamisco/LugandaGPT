"""Password, session, and role helpers for the Translation Studio."""

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from .db import record_audit, utc_now

ROLES = ("admin", "translator", "reviewer")
ROLE_LABELS = {
    "admin": "Administrator",
    "translator": "Translator",
    "reviewer": "Reviewer",
}
PUBLIC_PREFIX = {"admin": "A", "translator": "T", "reviewer": "R"}
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,40}$")
SESSION_HOURS = 12
PBKDF2_ITERATIONS = 310_000


class AuthError(ValueError):
    pass


def hash_password(password):
    if not isinstance(password, str) or len(password) < 10:
        raise AuthError("Password must be at least 10 characters.")
    if len(password) > 200:
        raise AuthError("Password must be at most 200 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return (
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password, salt_b64, hash_b64):
    try:
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(actual, expected)


def _next_public_id(connection, role):
    prefix = PUBLIC_PREFIX[role]
    rows = connection.execute(
        "SELECT public_id FROM users WHERE role = ?", (role,)
    ).fetchall()
    used = set()
    for row in rows:
        try:
            used.add(int(row["public_id"].split("-")[1]))
        except (IndexError, ValueError):
            continue
    number = 1
    while number in used:
        number += 1
    return f"{prefix}-{number:03d}"


def create_user(
    connection,
    username,
    display_name,
    role,
    password,
    actor_id=None,
):
    username = (username or "").strip()
    display_name = (display_name or "").strip()
    if not USERNAME_RE.match(username):
        raise AuthError(
            "Username must be 3 to 40 characters using letters, numbers, dots, dashes, or underscores."
        )
    if not display_name or len(display_name) > 100:
        raise AuthError("Display name is required and must be at most 100 characters.")
    if role not in ROLES:
        raise AuthError("Choose a valid role.")
    if connection.execute(
        "SELECT 1 FROM users WHERE username = ? COLLATE NOCASE", (username,)
    ).fetchone():
        raise AuthError("That username already exists.")
    salt, password_hash = hash_password(password)
    public_id = _next_public_id(connection, role)
    created = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO users(
            username, display_name, public_id, role, password_salt,
            password_hash, active, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """,
        (username, display_name, public_id, role, salt, password_hash, created),
    )
    user_id = cursor.lastrowid
    record_audit(
        connection,
        actor_id,
        "user_created",
        "user",
        user_id,
        {"username": username, "role": role, "public_id": public_id},
    )
    connection.commit()
    return user_id, public_id


def authenticate(connection, username, password):
    user = connection.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE AND active = 1",
        ((username or "").strip(),),
    ).fetchone()
    if not user:
        return None
    if not verify_password(password, user["password_salt"], user["password_hash"]):
        return None
    return user


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(connection, user_id):
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=SESSION_HOURS)
    connection.execute(
        """
        INSERT INTO sessions(token_hash, user_id, csrf_token, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            _token_hash(token),
            user_id,
            csrf_token,
            now.replace(microsecond=0).isoformat(),
            expires.replace(microsecond=0).isoformat(),
        ),
    )
    record_audit(connection, user_id, "login", "session", token[:8], {})
    connection.commit()
    return token, csrf_token


def get_session(connection, token):
    if not token:
        return None
    row = connection.execute(
        """
        SELECT s.*, u.id AS user_id, u.username, u.display_name, u.public_id,
               u.role, u.active
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND u.active = 1
        """,
        (_token_hash(token),),
    ).fetchone()
    if not row:
        return None
    if row["expires_at"] <= datetime.now(timezone.utc).replace(microsecond=0).isoformat():
        delete_session(connection, token)
        return None
    return row


def delete_session(connection, token, actor_id=None):
    if not token:
        return
    if actor_id:
        record_audit(connection, actor_id, "logout", "session", token[:8], {})
    connection.execute(
        "DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),)
    )
    connection.commit()


def require_role(user, roles):
    if not user or user["role"] not in roles:
        raise AuthError("You do not have permission to do that.")


def is_admin(user):
    return bool(user and user["role"] == "admin")


def is_translator(user):
    return bool(user and user["role"] == "translator")


def is_reviewer(user):
    return bool(user and user["role"] == "reviewer")
