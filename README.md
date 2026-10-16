# RTRC Library Management System Backend

FastAPI backend starter for the RTRC Library Management System.

## Stack

- FastAPI and Uvicorn
- PostgreSQL with SQLAlchemy 2 and Alembic
- JWT authentication foundations
- Optional MongoDB integration for legacy data

## Local development setup

### Requirements

- Python 3.11 or newer
- PostgreSQL
- MongoDB only if enabling legacy MongoDB-backed features

### Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a PostgreSQL database and configure the project-root `.env` file. The
application requires `SECRET_KEY`, `JWT_SECRET_KEY`, and either `DATABASE_URL`
or all of `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_USER`, and
`POSTGRES_PASSWORD`. `POSTGRES_PORT` defaults to `5432`; connection pool
settings also have defaults. Keep real credentials in `.env`, which is ignored
by Git.

For example, the separate PostgreSQL settings are:

```dotenv
SECRET_KEY=replace-with-a-random-secret
JWT_SECRET_KEY=replace-with-a-different-random-secret
POSTGRES_DB=rtrc_library
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-your-local-password
```

Alternatively, set only `DATABASE_URL` for the database connection. It must be
a SQLAlchemy-compatible PostgreSQL URL, for example:

```text
postgresql+psycopg2://user:password@localhost:5432/rtrc_library
```

If URL credentials contain reserved characters, URL-encode them. For hosted
PostgreSQL, include the provider's required TLS options in `DATABASE_URL`.
Generate strong values for both application secrets (for example,
`python -c "import secrets; print(secrets.token_urlsafe(32))"`).

### Database migrations

The initial Alembic migration creates the `library`, `members`, `circulation`,
and `content` schemas and the tables in the legacy `rtrclibrary.sql` dump,
alongside `public.roles` and `public.app_settings`. It seeds the role and
patron-category lookup rows, but does not copy legacy records.

The migration history is not yet an adoption plan for the existing live
database. The initial revision creates a legacy schema that differs from the
inspected database, while `0002_auth_roles` adds a membership-number unique
constraint and role row. The inspected live database has no `alembic_version`
table, and its membership numbers are not declared unique. Do **not** run
`alembic upgrade head`, `alembic stamp`, or a downgrade against that database
until a reviewed adoption baseline and migration plan have been prepared.

Validate the local model registry without connecting to PostgreSQL:

```bash
python -m compileall -q app/models migrations/env.py
python -c "import app.models; from sqlalchemy.orm import configure_mappers; from app.core.database import Base; configure_mappers(); print(len(Base.metadata.tables))"
```

The second command should report `18`. `alembic check` is read-only, but it
currently stops with `Target database is not up to date` because the live
database has no Alembic version table. After a safe adoption plan is in place,
it can compare metadata with the database without applying changes. The
existing initial migration's `downgrade()` drops tables and schemas; never run
it against data you need to keep.

### Run

```bash
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with interactive docs at
`http://127.0.0.1:8000/docs`. `GET /health/database` checks PostgreSQL
connectivity. Uploaded files go into the configured `UPLOAD_FOLDER` (default:
`uploads/`).

### Authentication

Do not apply migrations to an existing database until the adoption plan above
is complete. The auth models map the inspected existing schema; a superadmin
role must already exist before using the bootstrap command.

There is no public signup route. Create the initial superadmin once using a
hidden password prompt:

```bash
python -m app.cli --membership-number STAFF-001 --name "Library Administrator"
```

Every account, including staff accounts, uses a patron profile and a
membership number. A superadmin can create patrons or admins with
`POST /api/v1/auth/users`; an admin can create patrons only. The login endpoint
is `POST /api/v1/auth/login` and accepts OAuth2 form fields `username` (the
membership number) and `password`. It returns a bearer access token, valid for
`JWT_ACCESS_TOKEN_EXPIRES` seconds (one hour by default). Send it as
`Authorization: Bearer <access_token>` to `GET /api/v1/auth/me` or to protected
routes. Role checks load the current role from the database on each request.
Tokens are stateless and cannot be revoked individually; discard the token on
logout and it will expire at its configured lifetime.

When staff provisions a membership number that already belongs to a patron
without a user account, the existing patron profile is activated and assigned a
password without replacing the stored name or category. A patron already linked
to an account cannot be provisioned again.

Passwords must contain 12–128 characters and are stored as salted
PBKDF2-SHA256 hashes. The existing auth migration adds the `superadmin` role
and makes patron membership numbers unique; do not apply it to the live
database until its current roles, duplicate membership numbers, and adoption
history have been reviewed.
