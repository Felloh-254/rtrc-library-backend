"""Unit tests for authentication tokens, password hashing, and route wiring."""

import os
import unittest
from datetime import timedelta
from unittest.mock import patch

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
    verify_password,
)
from app.models.user import Patron, Role, User  # noqa: E402
from app.main import app  # noqa: E402
from app.schemas.auth import UserCreate  # noqa: E402
from app.services.auth import (  # noqa: E402
    DuplicateMembershipNumberError,
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
