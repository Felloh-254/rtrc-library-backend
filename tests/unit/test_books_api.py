"""Structural checks for book API documentation and request schemas."""

import unittest

from fastapi import FastAPI, HTTPException

from app.api.v1.books.routes import router as books_router
from app.core.dependencies import get_current_admin, get_current_user
from app.models.book import Book
from app.models.user import Role, User
from app.schemas.book import BookCopyCreate, BookCopyUpdate, BookCreate


class BookApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = FastAPI()
        self.app.include_router(books_router, prefix="/api/v1")
        self.openapi = self.app.openapi()

    def test_book_routes_are_documented_as_json_and_protected(self) -> None:
        expected_methods = {
            "/api/v1/books": {"get"},
            "/api/v1/books/metadata/{isbn}": {"get"},
            "/api/v1/books/{isbn}": {"get"},
            "/api/v1/books/copies": {"post"},
            "/api/v1/books/copies/{book_id}": {"put"},
        }
        for path, methods in expected_methods.items():
            self.assertEqual(
                {
                    method
                    for method in self.openapi["paths"][path]
                    if method in {"get", "post", "put", "patch", "delete"}
                },
                methods,
            )
            for method in methods:
                operation = self.openapi["paths"][path][method]
                self.assertIn("security", operation)
                success_status = "201" if method == "post" else "200"
                self.assertIn(success_status, operation["responses"])
                self.assertIn(
                    "application/json",
                    operation["responses"][success_status]["content"],
                )

    def test_book_writes_require_admin(self) -> None:
        for route in books_router.routes:
            methods = route.methods or set()
            if methods & {"POST", "PUT", "PATCH", "DELETE"}:
                dependency_calls = {
                    dependency.call for dependency in route.dependant.dependencies
                }
                self.assertIn(get_current_admin, dependency_calls)
            else:
                dependency_calls = {
                    dependency.call for dependency in route.dependant.dependencies
                }
                self.assertIn(get_current_user, dependency_calls)

    def test_admin_dependency_rejects_patron_and_accepts_admin_roles(self) -> None:
        def user_with_role(role_name: str) -> User:
            return User(role=Role(name=role_name))

        with self.assertRaises(HTTPException) as raised:
            get_current_admin(current_user=user_with_role("patron"))
        self.assertEqual(raised.exception.status_code, 403)

        for role_name in ("admin", "superadmin"):
            admin_user = user_with_role(role_name)
            self.assertIs(
                get_current_admin(current_user=admin_user),
                admin_user,
            )

    def test_request_lengths_and_copy_update_match_the_model(self) -> None:
        self.assertEqual(Book.__table__.c.book_title.type.length, 255)
        self.assertEqual(
            BookCreate.model_json_schema()["properties"]["title"]["maxLength"],
            255,
        )
        self.assertNotIn("book_id", BookCopyUpdate.model_fields)

        copy = BookCopyCreate.model_validate(
            {
                "book_account_number": "BOOK-00001",
                "isbn": "9780306406157",
                "acquisition_date": "2026-10-19T12:00:00",
                "acquisition_method": "Purchase",
            }
        )
        self.assertEqual(copy.account_number, "BOOK-00001")

    def test_openapi_describes_book_copy_request_and_responses(self) -> None:
        schemas = self.openapi["components"]["schemas"]
        post = self.openapi["paths"]["/api/v1/books/copies"]["post"]
        put = self.openapi["paths"]["/api/v1/books/copies/{book_id}"]["put"]

        self.assertEqual(
            post["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/BookCopyCreate",
        )
        self.assertEqual(
            put["requestBody"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/BookCopyUpdate",
        )
        self.assertIn("BookCopyRead", schemas)
        self.assertIn("BookMetadataRead", schemas)
        self.assertIn(
            "example",
            schemas["BookCopyCreate"],
        )
        self.assertIn(
            "example",
            schemas["BookCopyUpdate"],
        )
