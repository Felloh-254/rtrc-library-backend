"""Structural checks for the complete SQLAlchemy schema mappings."""

import unittest

import app.models
from sqlalchemy import CheckConstraint, Integer
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import configure_mappers

from app.core.database import Base


EXPECTED_TABLES = {
    "public.roles",
    "public.app_settings",
    "library.ddc_classifications",
    "library.patron_categories",
    "library.books",
    "library.ebooks",
    "members.patrons",
    "members.patron_contacts",
    "members.users",
    "circulation.borrowings",
    "circulation.borrowing_renewals",
    "circulation.fines",
    "circulation.requests",
    "circulation.reservations",
    "circulation.hold",
    "content.news",
    "content.events",
    "content.event_photos",
}


class ModelMetadataTests(unittest.TestCase):
    def test_all_reference_tables_are_registered(self) -> None:
        configure_mappers()
        self.assertEqual(set(Base.metadata.tables), EXPECTED_TABLES)

    def test_postgresql_array_columns_use_array_types(self) -> None:
        array_columns = {
            "library.books": {"book_author"},
            "library.ebooks": {"ebook_authors", "ebook_subjects"},
        }

        for table_name, columns in array_columns.items():
            table = Base.metadata.tables[table_name]
            for column_name in columns:
                self.assertIsInstance(table.c[column_name].type, ARRAY)

    def test_user_role_and_request_constraints_are_preserved(self) -> None:
        users = Base.metadata.tables["members.users"]
        role_constraints = [
            constraint
            for constraint in users.foreign_key_constraints
            if "user_role_id" in constraint.column_keys
        ]
        self.assertEqual(len(role_constraints), 2)
        self.assertEqual(
            {
                constraint.referred_table.fullname
                for constraint in role_constraints
            },
            {"public.roles"},
        )

        requests = Base.metadata.tables["circulation.requests"]
        check_names = {
            constraint.name
            for constraint in requests.constraints
            if isinstance(constraint, CheckConstraint)
        }
        self.assertEqual(
            check_names,
            {"chk_request_status", "requests_request_status_check"},
        )

    def test_live_user_timestamps_are_timezone_aware(self) -> None:
        users = Base.metadata.tables["members.users"]
        for name in ("user_last_login", "user_created_at", "user_updated_at"):
            self.assertTrue(users.c[name].type.timezone)

    def test_serial_primary_keys_use_integer_autoincrement(self) -> None:
        serial_tables = EXPECTED_TABLES - {
            "public.app_settings",
            "library.ddc_classifications",
        }
        for table_name in serial_tables:
            table = Base.metadata.tables[table_name]
            primary_key = next(iter(table.primary_key.columns))
            self.assertIsInstance(primary_key.type, Integer)
            self.assertTrue(primary_key.autoincrement)
