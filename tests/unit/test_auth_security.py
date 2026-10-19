"""Unit tests for authentication tokens, password hashing, and route wiring."""

import hashlib
import os
import unittest
from datetime import timedelta
from unittest.mock import patch

import bcrypt
from passlib.hash import pbkdf2_sha256 as passlib_pbkdf2_sha256

os.environ.setdefault("SECRET_KEY", "test-application-secret")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://test:test@localhost/test",
)

from app.core.security import (  # noqa: E402
    create_access_token,
    decode_access_token,
    hash_password,
    password_hash_needs_rehash,
    password_hash_scheme,
    verify_password,
)
from app.models.user import Patron, Role, User  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.auth import UserCreate  # noqa: E402
from app.services.auth import (  # noqa: E402
    DuplicateMembershipNumberError,
    InvalidCredentialsError,
    authenticate_user,
    create_account,
)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0
        self.refreshed: object | None = None

    def add(self, entity: object) -> None:
        self.added.append(entity)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, entity: object) -> None:
        self.refreshed = entity

    def rollback(self) -> None:
        return None


class AuthenticationSecurityTests(unittest.TestCase):
    def test_password_hash_verifies_only_the_original_password(self) -> None:
        password_hash = hash_password("correct horse battery staple")

        self.assertNotEqual(password_hash, "correct horse battery staple")
        self.assertTrue(verify_password("correct horse battery staple", password_hash))
        self.assertFalse(verify_password("incorrect password", password_hash))
        self.assertFalse(verify_password("anything", "invalid-hash"))
        self.assertFalse(verify_password("anything", None))

    def test_legacy_bcrypt_hash_verifies_and_requires_rehash(self) -> None:
        password = "correct horse battery staple"
        legacy_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()

        self.assertTrue(verify_password(password, legacy_hash))
        self.assertFalse(verify_password("incorrect password", legacy_hash))
        self.assertTrue(password_hash_needs_rehash(legacy_hash))

    def test_legacy_passlib_pbkdf2_hash_verifies_and_requires_rehash(self) -> None:
        password = "correct horse battery staple"
        legacy_hash = passlib_pbkdf2_sha256.using(rounds=10_000).hash(password)

        self.assertTrue(verify_password(password, legacy_hash))
        self.assertFalse(verify_password("incorrect password", legacy_hash))
        self.assertTrue(password_hash_needs_rehash(legacy_hash))
        self.assertEqual(password_hash_scheme(legacy_hash), "passlib-pbkdf2-sha256")

    def test_werkzeug_scrypt_hash_verifies_and_requires_rehash(self) -> None:
        password = "correct horse battery staple"
        salt = "mmmfu664L0OvrOFU"
        digest = hashlib.scrypt(
            password.encode(),
            salt=salt.encode(),
            n=32768,
            r=8,
            p=1,
            maxmem=128 * 1024 * 1024,
            dklen=64,
        )
        legacy_hash = f"scrypt:32768:8:1${salt}${digest.hex()}"

        self.assertTrue(verify_password(password, legacy_hash))
        self.assertFalse(verify_password("incorrect password", legacy_hash))
        self.assertTrue(password_hash_needs_rehash(legacy_hash))
        self.assertEqual(password_hash_scheme(legacy_hash), "werkzeug-scrypt")

    def test_scrypt_hash_rejects_unsafe_cost_parameters(self) -> None:
        self.assertFalse(
            verify_password(
                "password",
                "scrypt:1048576:16:4$salt$" + "00" * 64,
            )
        )

    def test_successful_legacy_login_upgrades_hash_and_trims_membership_number(self) -> None:
        db = FakeSession()
        password = "correct horse battery staple"
        legacy_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
        patron = Patron(
            id=8,
            membership_number="P-008",
            name="Existing Patron",
            password_hash=legacy_hash,
        )
        user = User(id=10, patron=patron, role=Role(id=2, name="patron"))
        upgraded_hash = hash_password("new password value")

        with (
            patch(
                "app.services.auth.get_user_by_membership_number",
                return_value=user,
            ) as get_user,
            patch("app.services.auth.hash_password", return_value=upgraded_hash),
        ):
            authenticated = authenticate_user(db, " P-008 ", password)

        get_user.assert_called_once_with(db, "P-008")
        self.assertIs(authenticated, user)
        self.assertEqual(patron.password_hash, upgraded_hash)
        self.assertEqual(db.commits, 1)

    def test_successful_passlib_login_upgrades_hash(self) -> None:
        db = FakeSession()
        password = "correct horse battery staple"
        legacy_hash = passlib_pbkdf2_sha256.using(rounds=10_000).hash(password)
        patron = Patron(
            id=8,
            membership_number="P-008",
            name="Existing Patron",
            password_hash=legacy_hash,
        )
        user = User(id=10, patron=patron, role=Role(id=2, name="admin"))
        upgraded_hash = hash_password(password)

        with (
            patch(
                "app.services.auth.get_user_by_membership_number",
                return_value=user,
            ),
            patch("app.services.auth.hash_password", return_value=upgraded_hash),
        ):
            authenticated = authenticate_user(db, "P-008", password)

        self.assertIs(authenticated, user)
        self.assertEqual(patron.password_hash, upgraded_hash)
        self.assertEqual(db.commits, 1)

    def test_successful_werkzeug_scrypt_login_upgrades_hash(self) -> None:
        db = FakeSession()
        password = "correct horse battery staple"
        salt = "mmmfu664L0OvrOFU"
        digest = hashlib.scrypt(
            password.encode(),
            salt=salt.encode(),
            n=32768,
            r=8,
            p=1,
            maxmem=128 * 1024 * 1024,
            dklen=64,
        )
        legacy_hash = f"scrypt:32768:8:1${salt}${digest.hex()}"
        patron = Patron(
            id=8,
            membership_number="P-008",
            name="Existing Patron",
            password_hash=legacy_hash,
        )
        user = User(id=10, patron=patron, role=Role(id=2, name="admin"))
        upgraded_hash = hash_password(password)

        with (
            patch(
                "app.services.auth.get_user_by_membership_number",
                return_value=user,
            ),
            patch("app.services.auth.hash_password", return_value=upgraded_hash),
        ):
            authenticated = authenticate_user(db, "P-008", password)

        self.assertIs(authenticated, user)
        self.assertEqual(patron.password_hash, upgraded_hash)
        self.assertEqual(db.commits, 1)

    def test_login_logs_missing_active_account_without_logging_credentials(self) -> None:
        db = FakeSession()
        membership_number = "PRIVATE-MEMBERSHIP"
        password = "private-password"

        with (
            patch(
                "app.services.auth.get_user_by_membership_number",
                return_value=None,
            ),
            self.assertLogs("app.services.auth", level="WARNING") as captured,
        ):
            with self.assertRaises(InvalidCredentialsError):
                authenticate_user(db, membership_number, password)

        self.assertIn("no active account matched", captured.output[0])
        self.assertNotIn(membership_number, captured.output[0])
        self.assertNotIn(password, captured.output[0])

    def test_login_logs_password_verification_failure(self) -> None:
        db = FakeSession()
        patron = Patron(
            id=8,
            membership_number="P-008",
            name="Existing Patron",
            password_hash=hash_password("different password"),
        )
        user = User(id=10, patron=patron, role=Role(id=2, name="admin"))
        password = "private-password"

        with (
            patch(
                "app.services.auth.get_user_by_membership_number",
                return_value=user,
            ),
            self.assertLogs("app.services.auth", level="WARNING") as captured,
        ):
            with self.assertRaises(InvalidCredentialsError):
                authenticate_user(db, "P-008", password)

        self.assertIn("password verification failed", captured.output[0])
        self.assertIn("account 10", captured.output[0])
        self.assertIn("stored format: pbkdf2_sha256", captured.output[0])
        self.assertNotIn(password, captured.output[0])
        self.assertNotIn(patron.password_hash, captured.output[0])

    def test_access_tokens_require_valid_subject_and_expiry(self) -> None:
        valid_token = create_access_token(42)
        expired_token = create_access_token(42, timedelta(seconds=-1))

        self.assertEqual(decode_access_token(valid_token), 42)
        self.assertIsNone(decode_access_token(expired_token))
        self.assertIsNone(decode_access_token("not-a-token"))

    def test_authentication_routes_are_registered(self) -> None:
        paths = app.openapi()["paths"]

        self.assertIn("/api/v1/auth/login", paths)
        self.assertIn("/api/v1/auth/me", paths)
        self.assertIn("/api/v1/auth/users", paths)

    def test_account_creation_activates_existing_patron_without_replacing_profile(self) -> None:
        db = FakeSession()
        patron = Patron(
            id=8,
            membership_number="P-008",
            name="Existing Patron",
            category_id=3,
        )
        role = Role(id=2, name="patron")
        request = UserCreate(
            membership_number="P-008",
            name="Ignored submitted name",
            password="a sufficiently long password",
        )

        with (
            patch("app.services.auth.get_patron_by_membership_number", return_value=patron),
            patch("app.services.auth.get_role_by_name", return_value=role),
            patch("app.services.auth.hash_password", return_value="test-hash"),
        ):
            user = create_account(db, request, "patron")

        self.assertEqual(patron.name, "Existing Patron")
        self.assertEqual(patron.password_hash, "test-hash")
        self.assertIs(user.patron, patron)
        self.assertIs(user.role, role)
        self.assertEqual(db.commits, 1)

    def test_account_creation_rejects_a_patron_who_already_has_a_user(self) -> None:
        db = FakeSession()
        patron = Patron(
            id=8,
            membership_number="P-008",
            name="Existing Patron",
        )
        patron.user = User(id=10, patron=patron, role=Role(id=2, name="patron"))
        request = UserCreate(
            membership_number="P-008",
            name="Existing Patron",
            password="a sufficiently long password",
        )

        with patch("app.services.auth.get_patron_by_membership_number", return_value=patron):
            with self.assertRaises(DuplicateMembershipNumberError):
                create_account(db, request, "patron")

        self.assertEqual(db.added, [])
        self.assertEqual(db.commits, 0)
