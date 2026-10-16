"""One-time account bootstrap commands."""

import argparse
from getpass import getpass

from app.core.database import SessionLocal
from app.schemas.auth import UserCreate
from app.services.auth import (
    DuplicateMembershipNumberError,
    SuperadminAlreadyExistsError,
    bootstrap_superadmin,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap an initial superadmin.")
    parser.add_argument("--membership-number", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    password = getpass("Superadmin password (minimum 12 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        parser.error("The passwords do not match.")

    try:
        account = UserCreate(
            membership_number=args.membership_number,
            name=args.name,
            password=password,
        )
    except ValueError as error:
        parser.error(str(error))

    with SessionLocal() as db:
        try:
            user = bootstrap_superadmin(db, account)
        except SuperadminAlreadyExistsError:
            parser.error("A superadmin account already exists.")
        except DuplicateMembershipNumberError:
            parser.error("That membership number is already in use.")
        if user.patron is None:
            raise RuntimeError("Created superadmin account has no patron profile.")
        created_membership_number = user.patron.membership_number

    print(f"Created superadmin account {created_membership_number}.")


if __name__ == "__main__":
    main()
