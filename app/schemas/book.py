
"""Pydantic request and response declarations for books."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StringConstraints


AccountNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=20),
]
ISBN = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=10, max_length=20),
]
BookTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

AcquisitionMethod = Literal["Purchase", "Donation", "Exchange"]
BookStatus = Literal["Available", "Issued", "Reserved", "Lost"]


class BookCreate(BaseModel):
    account_number: AccountNumber
    isbn: ISBN
    title: BookTitle
    authors: list[str] = Field(min_length=1)
    genre: str | None = None
    language: str | None = None
    publisher: str | None = None
    publication_year: str | None = None
    acquisition_method: AcquisitionMethod | None = None
    shelf_location: str | None = None
    condition: str | None = None
    ddc_code: str | None = None


class BookUpdate(BaseModel):
    account_number: AccountNumber | None = None
    isbn: ISBN | None = None
    title: BookTitle | None = None
    authors: list[str] | None = Field(default=None, min_length=1)
    genre: str | None = None
    language: str | None = None
    publisher: str | None = None
    publication_year: str | None = None
    acquisition_method: AcquisitionMethod | None = None
    shelf_location: str | None = None
    condition: str | None = None
    status: BookStatus | None = None
    ddc_code: str | None = None


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    isbn: str
    title: str
    authors: list[str]
    genre: str | None
    language: str | None
    publisher: str | None
    publication_year: str | None
    acquisition_method: str | None
    shelf_location: str | None
    condition: str | None
    status: str | None
    acquisition_date: datetime | None
    updation_date: datetime | None
    ddc_code: str | None


class BookCopyCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "account_number": "BOOK-00001",
                "isbn": "9780306406157",
                "acquisition_date": "2026-10-19T12:00:00",
                "acquisition_method": "Purchase",
                "condition": "Good",
                "shelf_location": "A1",
                "status": "Available",
            }
        }
    )

    account_number: AccountNumber = Field(
        validation_alias=AliasChoices("account_number", "book_account_number"),
    )
    isbn: ISBN
    acquisition_date: datetime
    acquisition_method: AcquisitionMethod
    condition: str | None = "Good"
    shelf_location: str | None = None
    status: BookStatus = "Available"


class BookCopyUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "acquisition_date": "2026-10-19T12:00:00",
                "acquisition_method": "Purchase",
                "shelf_location": "A1",
                "condition": "Good",
                "status": "Available",
            }
        }
    )

    acquisition_date: datetime
    acquisition_method: AcquisitionMethod
    shelf_location: str | None = None
    condition: str | None = None
    status: BookStatus


class BookMetadataRead(BaseModel):
    model_config = ConfigDict(extra="allow")

    isbn: str | None = None
    title: str | None = None
    authors: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    description: str = ""
    publisher: str = ""
    publishedDate: str = ""
    language: str = ""
    pageCount: int = 0
    imageLinks: dict[str, str] = Field(default_factory=dict)


class BookListItem(BookMetadataRead):
    copy_count: int = 0
    available_count: int = 0
    issued_count: int = 0
    reserved_count: int = 0
    lost_count: int = 0


class BookCopyRead(BaseModel):
    book_id: int
    book_account_number: str
    book_isbn: str
    acquisition_method: str | None = None
    shelf_location: str | None = None
    condition: str | None = None
    status: str | None = None
    acquisition_date: datetime | None = None
    updation_date: datetime | None = None


class BookListResponse(BaseModel):
    books: list[BookListItem]


class BookMetadataResponse(BaseModel):
    metadata: BookMetadataRead


class BookDetails(BaseModel):
    metadata: BookMetadataRead
    copies: list[BookCopyRead]
    copy_count: int


class BookDetailsResponse(BaseModel):
    data: BookDetails


class BookCopyCreateResponse(BaseModel):
    message: str
    metadata: BookMetadataRead


class BookCopyUpdateResponse(BaseModel):
    message: str
    data: BookCopyRead


class DDCClassificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    description: str
