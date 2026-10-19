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
by Git. MongoDB remains optional until Mongo-backed features are enabled; when
configured, the application verifies its connection at startup and closes the
client at shutdown.

To configure MongoDB with a full connection string:

```dotenv
MONGO_URI=mongodb+srv://user:password@cluster.example.mongodb.net/
MONGO_DB=rtrc_library
```

Alternatively, set `MONGO_CLUSTER` to the MongoDB host (or SRV URI), `MONGO_DB`
to the database name, and optionally set both `MONGO_USER` and `MONGO_PASS`.
`MONGO_SERVER_SELECTION_TIMEOUT_MS` controls the connection check timeout and
defaults to `5000`. `/health/database` reports the status of each configured
database; it reports MongoDB as `not_configured` when no MongoDB settings are
provided. Routes can access the selected Mongo database through the
`get_mongo_db` dependency.

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

#### Trying the books API in Swagger

The books API uses both PostgreSQL for physical copies and MongoDB for book
metadata, so configure and run both databases before testing these endpoints.
Open `/docs`, use **Authorize** to sign in with an admin or superadmin
membership number and password, and then try these routes in order:

1. `GET /api/v1/books/metadata/{isbn}` looks up metadata in MongoDB, or fetches
   it from Google Books and caches it. For example, try ISBN
   `9780306406157`.
2. `POST /api/v1/books/copies` adds a physical copy. Use a unique
   `account_number`, the same ISBN, an ISO date, and an acquisition method:

   ```json
   {
     "account_number": "BOOK-00001",
     "isbn": "9780306406157",
     "acquisition_date": "2026-10-19T12:00:00",
     "acquisition_method": "Purchase",
     "condition": "Good",
     "shelf_location": "A1",
     "status": "Available"
   }
   ```

3. `GET /api/v1/books` lists metadata with physical-copy counts.
   `GET /api/v1/books/{isbn}` returns the metadata and individual copies.
4. `PUT /api/v1/books/copies/{book_id}` edits a copy. Set `book_id` in the path
   to the ID returned by the details endpoint. The request body accepts
   `acquisition_date`, `acquisition_method`, `shelf_location`, `condition`, and
   `status`; the copy ID itself is not editable.

All books routes require a valid bearer token. Listing, metadata lookup, and
details are available to any authenticated user; adding and updating copies
require an admin or superadmin. Invalid request fields are described in the
Swagger request schemas.

No books migration is needed for this API wiring: the existing `Book` model's
columns and constraints match the `library.books` table defined in migration
`0001_legacy_postgres_schema`. Route, service, and request/response schema
changes do not alter the database structure.

Application logs are written to the server console with a timestamp, severity,
and module name. Use `logging.getLogger(__name__)` in application modules;
`logger.exception(...)` inside an exception handler records the traceback.
Unexpected API exceptions are logged and returned as a generic HTTP 500 response.

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
PBKDF2-SHA256 hashes. Existing bcrypt, Passlib PBKDF2-SHA256, and Werkzeug
scrypt hashes are accepted and upgraded to the current PBKDF2-SHA256 format
after a successful login. The existing auth migration adds the `superadmin`
role and makes patron membership numbers unique; do not apply it to the live
database until its current roles, duplicate membership numbers, and adoption
history have been reviewed.
