"""Add the superadmin role and enforce unique membership numbers.

Revision ID: 0002_auth_roles
Revises: 0001_legacy_schema
Create Date: 2026-10-16
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0002_auth_roles"
down_revision: Union[str, None] = "0001_legacy_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO public.roles (role_name) VALUES ('superadmin') "
        "ON CONFLICT (role_name) DO NOTHING"
    )
    op.create_unique_constraint(
        "uq_patrons_membership_number",
        "patrons",
        ["patron_membership_number"],
        schema="members",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_patrons_membership_number",
        "patrons",
        schema="members",
        type_="unique",
    )
    op.execute("""
        DELETE FROM public.roles
        WHERE role_name = 'superadmin'
          AND NOT EXISTS (
              SELECT 1
              FROM members.users
              WHERE members.users.user_role_id = public.roles.role_id
          )
    """)
