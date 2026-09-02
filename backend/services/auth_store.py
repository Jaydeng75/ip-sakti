"""Persistent authentication storage for horizontally scaled deployments.

The application database remains the owner of case relationships. In production,
Firestore is the durable source of truth for credentials and token revocations;
each Cloud Run instance reconstructs a local SQL user mirror as needed.
"""

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from config import settings


class AuthStoreError(RuntimeError):
    """Raised when the configured persistent authentication service is unavailable."""


class AccountAlreadyExists(AuthStoreError):
    """Raised when registration is attempted for an existing normalized email."""


@dataclass(frozen=True)
class AuthRecord:
    subject: str
    email: str
    display_name: str
    password_hash: str
    role: str = "analyst"
    is_active: bool = True


def normalized_email(email: str) -> str:
    return email.strip().lower()


def subject_for_email(email: str) -> str:
    """Return a stable, opaque JWT subject and Firestore document identifier."""
    return hashlib.sha256(normalized_email(email).encode("utf-8")).hexdigest()


def persistent_auth_enabled() -> bool:
    return settings.auth_store_provider.strip().lower() == "firestore"


@lru_cache(maxsize=1)
def _client():
    try:
        from google.cloud import firestore

        return firestore.Client(
            project=settings.firestore_project or settings.google_cloud_project,
            database=settings.firestore_database,
        )
    except Exception as exc:  # pragma: no cover - depends on deployment credentials
        raise AuthStoreError("Persistent authentication storage is unavailable") from exc


def _user_ref(subject: str):
    return _client().collection(settings.firestore_auth_collection).document(subject)


def _record_from_snapshot(snapshot) -> AuthRecord | None:
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    required = {"email", "display_name", "password_hash"}
    if not required.issubset(data):
        raise AuthStoreError("Persistent account record is incomplete")
    return AuthRecord(
        subject=snapshot.id,
        email=normalized_email(str(data["email"])),
        display_name=str(data["display_name"]),
        password_hash=str(data["password_hash"]),
        role=str(data.get("role") or "analyst"),
        is_active=bool(data.get("is_active", True)),
    )


def create_account(
    *,
    email: str,
    display_name: str,
    password_hash: str,
    role: str = "analyst",
    is_active: bool = True,
) -> AuthRecord:
    from google.api_core.exceptions import AlreadyExists, GoogleAPICallError

    clean_email = normalized_email(email)
    subject = subject_for_email(clean_email)
    record = AuthRecord(subject, clean_email, display_name.strip(), password_hash, role, is_active)
    try:
        _user_ref(subject).create(
            {
                "email": record.email,
                "display_name": record.display_name,
                "password_hash": record.password_hash,
                "role": record.role,
                "is_active": record.is_active,
                "schema_version": 1,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        )
    except AlreadyExists as exc:
        raise AccountAlreadyExists("An account with this email already exists") from exc
    except GoogleAPICallError as exc:
        raise AuthStoreError("Persistent authentication storage is unavailable") from exc
    return record


def get_account_by_email(email: str) -> AuthRecord | None:
    return get_account_by_subject(subject_for_email(email))


def get_account_by_subject(subject: str) -> AuthRecord | None:
    try:
        return _record_from_snapshot(_user_ref(subject).get())
    except AuthStoreError:
        raise
    except Exception as exc:
        raise AuthStoreError("Persistent authentication storage is unavailable") from exc


def revoke_token(*, jti: str, subject: str, expires_at: datetime) -> None:
    try:
        _client().collection(settings.firestore_revocation_collection).document(jti).set(
            {
                "subject": subject,
                "expires_at": expires_at,
                "revoked_at": datetime.now(UTC),
            }
        )
    except Exception as exc:
        raise AuthStoreError("Persistent authentication storage is unavailable") from exc


def token_is_revoked(jti: str) -> bool:
    try:
        snapshot = _client().collection(settings.firestore_revocation_collection).document(jti).get()
        return bool(snapshot.exists)
    except Exception as exc:
        raise AuthStoreError("Persistent authentication storage is unavailable") from exc
