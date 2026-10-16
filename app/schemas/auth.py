"""Pydantic request and response declarations for authentication."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


MembershipNumber = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20),
]
AccountName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50),
]
Password = Annotated[str, Field(min_length=12, max_length=128)]


class UserCreate(BaseModel):
    membership_number: MembershipNumber
    name: AccountName
    password: Password
    role: Literal["patron", "admin"] = "patron"
    category_id: int | None = Field(default=None, ge=1)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    membership_number: str
    name: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class TokenSubject(BaseModel):
    user_id: int