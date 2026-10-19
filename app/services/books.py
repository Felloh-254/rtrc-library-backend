"""Business logic for book metadata and physical copies."""

import json
import logging
from collections.abc import Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from pymongo.collection import Collection
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import normalize_isbn_value
from app.repositories.books import (
    get_all_books as repo_get_all_books,
    get_book_copies_by_isbn as repo_get_book_copies_by_isbn,
    get_book_metadata_from_mongo,
    insert_book_copy as repo_insert_book_copy,
    save_book_metadata_to_mongo,
    update_book_copy as repo_update_book_copy,
)

logger = logging.getLogger(__name__)

_ACQUISITION_METHODS = {"Purchase", "Donation", "Exchange"}
_BOOK_STATUSES = {"Available", "Issued", "Reserved", "Lost"}


class BookServiceError(RuntimeError):
    """Raised when a book operation fails unexpectedly."""


def get_all_books(
    db: Session,
    collection: Collection[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return books and their copy counts."""
    books, error = repo_get_all_books(db, collection)
    if error:
        logger.error("Failed to fetch books: %s", error)
        raise BookServiceError("Failed to fetch books")
    return books or []


def serialize_book_copy(copy: Mapping[str, Any]) -> dict[str, Any]:
    """Convert a database copy row into a JSON-friendly dictionary."""
    serialized = dict(copy)
    for key in ("acquisition_date", "updation_date"):
        value = serialized.get(key)
        if hasattr(value, "isoformat"):
            serialized[key] = value.isoformat()
    return serialized


def fetch_book_metadata_from_google(isbn: str) -> dict[str, Any] | None:
    """Look up book metadata from the Google Books API."""
    normalized_isbn = normalize_isbn_value(isbn)
    if not normalized_isbn:
        logger.warning("Cannot look up Google Books metadata for an invalid ISBN")
        return None

    if not settings.GOOGLE_BOOKS_API_URL:
        logger.error("Google Books API URL is not configured")
        return None

    query: dict[str, str] = {"q": f"isbn:{normalized_isbn}"}
    if settings.GOOGLE_BOOKS_API_KEY:
        query["key"] = settings.GOOGLE_BOOKS_API_KEY
    separator = "&" if "?" in settings.GOOGLE_BOOKS_API_URL else "?"
    url = f"{settings.GOOGLE_BOOKS_API_URL}{separator}{urlencode(query)}"

    try:
        with urlopen(url, timeout=10) as response:
            payload = json.load(response)
    except HTTPError as error:
        logger.error(
            "Google Books request failed for ISBN %s with HTTP %s",
            normalized_isbn,
            error.code,
        )
        return None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        logger.exception(
            "Error fetching Google Books metadata for ISBN %s",
            normalized_isbn,
        )
        return None

    if not isinstance(payload, dict):
        logger.warning(
            "Google Books returned an invalid response for ISBN %s",
            normalized_isbn,
        )
        return None

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        logger.info("Google Books returned no metadata for ISBN %s", normalized_isbn)
        return None

    first_item = items[0]
    if not isinstance(first_item, dict):
        logger.warning(
            "Google Books returned an invalid item for ISBN %s",
            normalized_isbn,
        )
        return None

    volume_info = first_item.get("volumeInfo")
    if not isinstance(volume_info, dict):
        logger.warning(
            "Google Books item has no volume information for ISBN %s",
            normalized_isbn,
        )
        return None

    authors = volume_info.get("authors")
    categories = volume_info.get("categories")
    return {
        "isbn": normalized_isbn,
        "title": volume_info.get("title"),
        "authors": authors if isinstance(authors, list) else [],
        "categories": categories if isinstance(categories, list) else [],
        "description": volume_info.get("description", ""),
        "publisher": volume_info.get("publisher", ""),
        "publishedDate": volume_info.get("publishedDate", ""),
        "language": volume_info.get("language", ""),
        "pageCount": volume_info.get("pageCount", 0),
        "imageLinks": volume_info.get("imageLinks", {}),
    }


def get_or_fetch_book_metadata(
    isbn: str,
    collection: Collection[dict[str, Any]],
) -> dict[str, Any] | None:
    """Return cached metadata or fetch it from Google Books and cache it."""
    normalized_isbn = normalize_isbn_value(isbn)
    if not normalized_isbn:
        return None

    metadata = get_book_metadata_from_mongo(normalized_isbn, collection)
    if metadata:
        return metadata

    metadata = fetch_book_metadata_from_google(normalized_isbn)
    if metadata and not save_book_metadata_to_mongo(metadata, collection):
        logger.warning("Could not cache metadata for ISBN %s", normalized_isbn)
    return metadata


def get_book_details_by_isbn(
    db: Session,
    isbn: str,
    collection: Collection[dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    """Get MongoDB metadata and PostgreSQL copies for an ISBN."""
    normalized_isbn = normalize_isbn_value(isbn)
    if not normalized_isbn:
        return None, "ISBN is required"

    metadata = get_book_metadata_from_mongo(normalized_isbn, collection)
    if not metadata:
        return None, "Book metadata not found"

    copies, error = repo_get_book_copies_by_isbn(db, normalized_isbn)
    if error:
        logger.error("Failed to fetch copies for ISBN %s: %s", normalized_isbn, error)
        return None, error

    serialized_copies = [serialize_book_copy(copy) for copy in copies or []]
    return {
        "metadata": metadata,
        "copies": serialized_copies,
        "copy_count": len(serialized_copies),
    }, None


def update_book_copy(
    db: Session,
    original_book_id: int,
    copy_data: Mapping[str, Any],
) -> tuple[bool, str, dict[str, Any] | None]:
    """Update editable fields on a physical book copy."""
    if not isinstance(copy_data, Mapping):
        return False, "Invalid payload format", None

    acquisition_method = copy_data.get("acquisition_method")
    acquisition_date = copy_data.get("acquisition_date")
    status = copy_data.get("status")
    if not original_book_id or not acquisition_date:
        return False, "Missing required copy fields", None
    if acquisition_method not in _ACQUISITION_METHODS:
        return False, "Invalid acquisition method", None
    if status not in _BOOK_STATUSES:
        return False, "Invalid book status", None

    editable_data = {
        "acquisition_method": acquisition_method,
        "acquisition_date": acquisition_date,
        "shelf_location": (copy_data.get("shelf_location") or "").strip(),
        "condition": (copy_data.get("condition") or "").strip(),
        "status": status,
    }
    updated, error = repo_update_book_copy(db, original_book_id, editable_data)
    if error:
        logger.error("Failed to update book copy %s: %s", original_book_id, error)
        return False, error, None
    if not updated:
        return False, "Book copy not found", None

    return True, "Book copy updated successfully", serialize_book_copy(updated)


def add_book_copy(
    db: Session,
    book_data: Mapping[str, Any],
    collection: Collection[dict[str, Any]],
) -> tuple[bool, str, dict[str, Any] | None]:
    """Add a physical copy, fetching metadata when it is not cached."""
    if not isinstance(book_data, Mapping):
        return False, "Invalid payload format", None

    isbn = normalize_isbn_value(book_data.get("isbn"))
    account_number = book_data.get(
        "account_number",
        book_data.get("book_account_number"),
    )
    acquisition_date = book_data.get("acquisition_date")
    acquisition_method = book_data.get("acquisition_method")

    if not all((isbn, account_number, acquisition_date, acquisition_method)):
        return False, "Missing required fields", None
    if acquisition_method not in _ACQUISITION_METHODS:
        return False, "Invalid acquisition method", None

    metadata = get_or_fetch_book_metadata(isbn, collection)
    if not metadata:
        return False, "No metadata found for this ISBN", None
    title = metadata.get("title")
    if not isinstance(title, str) or not title.strip():
        return False, "Book metadata is missing a title", None

    categories = metadata.get("categories")
    if isinstance(categories, list):
        genre = ", ".join(
            category for category in categories if isinstance(category, str)
        )
    else:
        genre = metadata.get("genre")
    insert_data = {
        "account_number": str(account_number).strip(),
        "isbn": isbn,
        "title": title.strip(),
        "authors": metadata.get("authors") or [],
        "genre": genre,
        "language": metadata.get("language"),
        "publisher": metadata.get("publisher"),
        "publication_year": metadata.get(
            "publishedDate",
            metadata.get("publication_year"),
        ),
        "acquisition_date": acquisition_date,
        "acquisition_method": acquisition_method,
        "shelf_location": book_data.get("shelf_location"),
        "condition": book_data.get("condition", "Good"),
        "status": book_data.get("status", "Available"),
    }

    success, error = repo_insert_book_copy(db, insert_data)
    if not success:
        message = error or "Failed to add book copy"
        logger.error("Could not add book copy for ISBN %s: %s", isbn, message)
        return False, message, None

    return True, "Book copy added successfully", metadata
