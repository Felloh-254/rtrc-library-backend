"""Repository operations for book metadata and physical copies."""

import logging
from datetime import datetime
from typing import Any

from pymongo.collection import Collection
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.models.book import Book
from app.core.dependencies import normalize_isbn_value, build_isbn_regex

logger = logging.getLogger(__name__)


def get_all_books(
    db: Session,
    collection: Collection[dict[str, Any]],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Fetch MongoDB metadata with PostgreSQL copy counts."""
    try:
        statement = (
            select(
                Book.isbn,
                func.count(Book.id).label("copy_count"),
                func.sum(
                    case((Book.status == "Available", 1), else_=0)
                ).label("available_count"),
                func.sum(
                    case((Book.status == "Issued", 1), else_=0)
                ).label("issued_count"),
                func.sum(
                    case((Book.status == "Reserved", 1), else_=0)
                ).label("reserved_count"),
                func.sum(
                    case((Book.status == "Lost", 1), else_=0)
                ).label("lost_count"),
            )
            .group_by(Book.isbn)
        )

        copy_counts = {}

        for row in db.execute(statement).mappings():
            isbn = normalize_isbn_value(row["isbn"])

            if not isbn:
                continue

            counts = copy_counts.setdefault(
                isbn,
                {
                    "copy_count": 0,
                    "available_count": 0,
                    "issued_count": 0,
                    "reserved_count": 0,
                    "lost_count": 0,
                },
            )

            for key in counts:
                counts[key] += row[key] or 0

        mongo_books = list(
            collection.find({}, {"_id": 0}).sort(
                [("title", 1), ("isbn", 1)]
            )
        )

        for book in mongo_books:
            isbn = normalize_isbn_value(book.get("isbn"))
            counts = copy_counts.get(isbn, {})

            book.update(
                {
                    "copy_count": counts.get("copy_count", 0),
                    "available_count": counts.get("available_count", 0),
                    "issued_count": counts.get("issued_count", 0),
                    "reserved_count": counts.get("reserved_count", 0),
                    "lost_count": counts.get("lost_count", 0),
                }
            )

        return mongo_books, None

    except Exception:
        logger.exception("Error fetching books")
        return None, "Failed to fetch books"


def get_book_copies_by_isbn(db: Session, isbn: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Fetch PostgreSQL copies associated with an ISBN."""
    try:
        normalized_isbn = normalize_isbn_value(isbn)

        normalized_db_isbn = func.regexp_replace(
            Book.isbn,
            "[^[:alnum:]]",
            "",
            "g",
        )

        statement = (
            select(
                Book.id.label("book_id"),
                Book.account_number.label("book_account_number"),
                Book.isbn.label("book_isbn"),
                Book.acquisition_method,
                Book.shelf_location,
                Book.condition,
                Book.status,
                Book.acquisition_date,
                Book.updation_date,
            )
            .where(
                (Book.isbn == isbn)
                | (normalized_db_isbn == normalized_isbn)
            )
            .order_by(Book.acquisition_date.desc(), Book.id)
        )

        return [dict(row) for row in db.execute(statement).mappings()], None

    except Exception:
        logger.exception("Error fetching book copies")
        return None, "Failed to fetch book copies"


def update_book_copy(
    db: Session,
    original_book_id: int,
    copy_data: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    """Update editable fields of a PostgreSQL book copy."""
    try:
        statement = (
            update(Book)
            .where(Book.id == original_book_id)
            .values(
                acquisition_method=copy_data["acquisition_method"],
                acquisition_date=copy_data["acquisition_date"],
                shelf_location=copy_data.get("shelf_location"),
                condition=copy_data.get("condition"),
                status=copy_data["status"],
                updation_date=func.current_timestamp(),
            )
            .returning(
                Book.id.label("book_id"),
                Book.isbn.label("book_isbn"),
                Book.acquisition_method,
                Book.shelf_location,
                Book.condition,
                Book.status,
                Book.acquisition_date,
                Book.updation_date,
            )
        )

        updated = db.execute(statement).mappings().one_or_none()
        db.commit()

        return (dict(updated) if updated else None), None

    except Exception:
        db.rollback()
        logger.exception("Error updating book copy")
        return None, "Failed to update book copy"


def get_book_metadata_from_mongo(
    isbn: str,
    collection: Collection[dict[str, Any]],
) -> dict[str, Any] | None:
    """Find book metadata in MongoDB."""
    try:
        normalized_isbn = normalize_isbn_value(isbn)
        isbn_regex = build_isbn_regex(isbn)

        query = {
            "$or": [
                {"isbn": isbn},
                {"isbn": normalized_isbn},
                {"isbn": {"$regex": isbn_regex, "$options": "i"}},
            ]
        }

        return collection.find_one(query, {"_id": 0})

    except Exception:
        logger.exception("Error fetching book metadata from MongoDB")
        return None


def save_book_metadata_to_mongo(
    metadata: dict[str, Any],
    collection: Collection[dict[str, Any]],
) -> bool:
    """Save book metadata to MongoDB."""
    try:
        collection.insert_one(metadata)
        return True

    except Exception:
        logger.exception("Error saving book metadata to MongoDB")
        return False


def insert_book_copy(db: Session, book_data: dict[str, Any]) -> tuple[bool, str | None]:
    """Insert a physical copy into PostgreSQL."""
    try:
        book = Book(
            account_number=book_data["account_number"],
            isbn=book_data["isbn"],
            title=book_data["title"],
            authors=book_data["authors"],
            genre=book_data.get("genre"),
            language=book_data.get("language"),
            publisher=book_data.get("publisher"),
            publication_year=book_data.get("publication_year"),
            acquisition_date=book_data.get(
                "acquisition_date",
                datetime.now(),
            ),
            acquisition_method=book_data.get("acquisition_method"),
            shelf_location=book_data.get("shelf_location"),
            condition=book_data.get("condition"),
            status=book_data.get("status", "Available"),
        )

        db.add(book)
        db.commit()
        db.refresh(book)

        return True, None

    except Exception:
        db.rollback()
        logger.exception("Error inserting book copy")
        return False, "Failed to insert book copy"
