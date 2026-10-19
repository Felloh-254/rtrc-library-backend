"""JSON endpoints for book metadata and physical copies."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.collection import Collection
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_admin,
    get_current_user,
    get_db,
    get_mongo_books_collection,
)
from app.schemas.book import (
    BookCopyCreate,
    BookCopyCreateResponse,
    BookCopyUpdate,
    BookCopyUpdateResponse,
    BookDetailsResponse,
    BookListResponse,
    BookMetadataResponse,
)
from app.services import books as book_service


router = APIRouter(
    prefix="/books",
    tags=["Books"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=BookListResponse)
def list_books(
    db: Session = Depends(get_db),
    collection: Collection[dict[str, Any]] = Depends(get_mongo_books_collection),
) -> dict[str, Any]:
    """List books with their physical-copy counts."""
    try:
        return {"books": book_service.get_all_books(db, collection)}
    except book_service.BookServiceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(error),
        ) from error


@router.get("/metadata/{isbn}", response_model=BookMetadataResponse)
def fetch_book_metadata(
    isbn: str,
    collection: Collection[dict[str, Any]] = Depends(get_mongo_books_collection),
) -> dict[str, Any]:
    """Fetch cached or remote metadata for an ISBN."""
    metadata = book_service.get_or_fetch_book_metadata(isbn, collection)
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book metadata not found",
        )
    return {"metadata": metadata}


@router.get("/{isbn}", response_model=BookDetailsResponse)
def get_book_details(
    isbn: str,
    db: Session = Depends(get_db),
    collection: Collection[dict[str, Any]] = Depends(get_mongo_books_collection),
) -> dict[str, Any]:
    """Get book metadata and its physical copies."""
    details, error = book_service.get_book_details_by_isbn(db, isbn, collection)
    if error:
        if error == "Book metadata not found":
            status_code = status.HTTP_404_NOT_FOUND
        elif error == "ISBN is required":
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        raise HTTPException(status_code=status_code, detail=error)
    return {"data": details}


@router.post(
    "/copies",
    response_model=BookCopyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_book_copy(
    data: BookCopyCreate,
    db: Session = Depends(get_db),
    collection: Collection[dict[str, Any]] = Depends(get_mongo_books_collection),
    _admin=Depends(get_current_admin),
) -> dict[str, Any]:
    """Add a physical copy; only administrators can write book records."""
    success, message, metadata = book_service.add_book_copy(
        db,
        data.model_dump(),
        collection,
    )
    if not success:
        if message == "No metadata found for this ISBN":
            status_code = status.HTTP_404_NOT_FOUND
        elif message.startswith("Failed to"):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=message)
    return {"message": message, "metadata": metadata}


@router.put("/copies/{book_id}", response_model=BookCopyUpdateResponse)
def update_book_copy(
    book_id: int,
    data: BookCopyUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
) -> dict[str, Any]:
    """Update editable copy fields without changing the copy's identifier."""
    success, message, updated = book_service.update_book_copy(
        db,
        book_id,
        data.model_dump(),
    )
    if not success:
        if message == "Book copy not found":
            status_code = status.HTTP_404_NOT_FOUND
        elif message.startswith("Failed to"):
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=message)
    return {"message": message, "data": updated}
