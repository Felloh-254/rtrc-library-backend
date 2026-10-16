-- ============================================================
-- RTRC Library — Existing PostgreSQL Schema Reference
-- Reconstructed from inspection of the live database.
-- DO NOT execute against the existing live database.
-- ============================================================

-- =====================
-- public
-- =====================

CREATE TABLE public.roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE public.app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- library
-- =====================

CREATE TABLE library.ddc_classifications (
    ddc_code VARCHAR(20) PRIMARY KEY,
    ddc_description TEXT NOT NULL
);

CREATE TABLE library.patron_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE NOT NULL,
    CONSTRAINT patron_categories_category_name_check
        CHECK (
            category_name IN (
                'Primary Student',
                'Secondary Student',
                'TVET Student',
                'Teacher',
                'Community Member'
            )
        )
);

CREATE TABLE library.books (
    book_id SERIAL PRIMARY KEY,
    book_account_number VARCHAR(20) NOT NULL,
    book_isbn VARCHAR(20) NOT NULL,
    book_title VARCHAR(255) NOT NULL,
    book_author TEXT[] NOT NULL,
    book_genre VARCHAR(255),
    book_language VARCHAR(50),
    book_publisher VARCHAR(255),
    book_publication_year VARCHAR(20),
    book_acquisition_method VARCHAR(50),
    book_shelf_location VARCHAR(100),
    book_condition VARCHAR(50),
    book_status VARCHAR(50) DEFAULT 'Available',
    book_acquisition_date TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP,
    book_updation_date TIMESTAMP WITHOUT TIME ZONE
        DEFAULT CURRENT_TIMESTAMP,
    book_ddc_code VARCHAR(20),

    CONSTRAINT fk_books_ddc
        FOREIGN KEY (book_ddc_code)
        REFERENCES library.ddc_classifications(ddc_code),

    CONSTRAINT books_acquisition_method_check
        CHECK (
            book_acquisition_method IN ('Purchase', 'Donation', 'Exchange')
        ),

    CONSTRAINT books_status_check
        CHECK (
            book_status IN ('Available', 'Issued', 'Reserved', 'Lost')
        )
);

CREATE TABLE library.ebooks (
    ebook_id SERIAL PRIMARY KEY,
    ebook_isbn VARCHAR(20) NOT NULL,
    ebook_gutenberg_id INTEGER UNIQUE,
    ebook_title VARCHAR(255),
    ebook_authors TEXT[],
    ebook_language VARCHAR(50),
    ebook_format VARCHAR(50) NOT NULL,
    ebook_download_url TEXT NOT NULL,
    ebook_download_count INTEGER DEFAULT 0,
    ebook_added_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ebook_added_by VARCHAR(20),
    ebook_cover_url TEXT,
    ebook_subjects TEXT[],
    ebook_copyright BOOLEAN
);

-- =====================
-- members
-- =====================

CREATE TABLE members.patrons (
    patron_id SERIAL PRIMARY KEY,
    patron_membership_number VARCHAR(20) NOT NULL,
    patron_name VARCHAR(50) NOT NULL,
    patron_gender VARCHAR(10),
    patron_date_of_birth DATE,
    patron_education_level VARCHAR(50),
    patron_locality TEXT,
    patron_password TEXT,
    patron_category_id INTEGER,

    CONSTRAINT fk_patrons_category
        FOREIGN KEY (patron_category_id)
        REFERENCES library.patron_categories(category_id),

    CONSTRAINT patrons_gender_check
        CHECK (patron_gender IN ('Male', 'Female', 'Other')),

    CONSTRAINT patrons_education_level_check
        CHECK (
            patron_education_level IN ('Primary', 'Secondary', 'Tertiary', 'Other')
        )
);

CREATE TABLE members.patron_contacts (
    contact_id SERIAL PRIMARY KEY,
    patron_id INTEGER NOT NULL,
    contact_type VARCHAR(20),
    contact_value TEXT NOT NULL,

    CONSTRAINT patron_contacts_patron_id_fkey
        FOREIGN KEY (patron_id)
        REFERENCES members.patrons(patron_id),

    CONSTRAINT patron_contacts_contact_type_check
        CHECK (contact_type IN ('Phone', 'Email', 'WhatsApp'))
);

CREATE TABLE members.users (
    user_id SERIAL PRIMARY KEY,
    user_patron_id INTEGER UNIQUE,
    user_role_id INTEGER NOT NULL DEFAULT 2,
    user_date_joined DATE NOT NULL DEFAULT CURRENT_DATE,
    user_status BOOLEAN NOT NULL DEFAULT TRUE,
    user_last_login TIMESTAMP WITHOUT TIME ZONE,
    user_created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    user_deleted BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT users_user_patron_id_fkey
        FOREIGN KEY (user_patron_id)
        REFERENCES members.patrons(patron_id),

    CONSTRAINT users_user_role_id_fkey
        FOREIGN KEY (user_role_id)
        REFERENCES members.roles(role_id),

    CONSTRAINT users_not_deleted_active_check
        CHECK (NOT (user_deleted = TRUE AND user_status = TRUE))
);

-- =====================
-- circulation
-- =====================

CREATE TABLE circulation.borrowings (
    borrowing_id SERIAL PRIMARY KEY,
    borrowing_patron_id INTEGER NOT NULL,
    borrowing_book_id INTEGER NOT NULL,
    borrowing_date DATE NOT NULL DEFAULT CURRENT_DATE,
    borrowing_due_date DATE NOT NULL,
    borrowing_return_date DATE,
    borrowing_status VARCHAR(20) DEFAULT 'Borrowed',
    borrowing_renewal_count INTEGER NOT NULL DEFAULT 0,

    CONSTRAINT borrowings_borrowing_patron_id_fkey
        FOREIGN KEY (borrowing_patron_id)
        REFERENCES members.patrons(patron_id),

    CONSTRAINT borrowings_borrowing_book_id_fkey
        FOREIGN KEY (borrowing_book_id)
        REFERENCES library.books(book_id),

    CONSTRAINT borrowings_borrowing_status_check
        CHECK (borrowing_status IN ('Borrowed', 'Returned', 'Overdue'))
);

CREATE TABLE circulation.borrowing_renewals (
    renewal_id SERIAL PRIMARY KEY,
    borrowing_id INTEGER,
    renewed_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    old_due_date DATE,
    new_due_date DATE,

    CONSTRAINT borrowing_renewals_borrowing_id_fkey
        FOREIGN KEY (borrowing_id)
        REFERENCES circulation.borrowings(borrowing_id)
);

CREATE TABLE circulation.fines (
    fine_id SERIAL PRIMARY KEY,
    fine_borrowing_id INTEGER NOT NULL,
    fine_amount NUMERIC(10, 2) NOT NULL,
    fine_paid BOOLEAN DEFAULT FALSE,

    CONSTRAINT fines_fine_borrowing_id_fkey
        FOREIGN KEY (fine_borrowing_id)
        REFERENCES circulation.borrowings(borrowing_id)
);

CREATE TABLE circulation.requests (
    request_id SERIAL PRIMARY KEY,
    request_patron_id INTEGER NOT NULL,
    request_book_id INTEGER NOT NULL,
    request_date DATE NOT NULL DEFAULT CURRENT_DATE,
    request_status VARCHAR(20) DEFAULT 'Active',

    CONSTRAINT requests_request_patron_id_fkey
        FOREIGN KEY (request_patron_id)
        REFERENCES members.patrons(patron_id),

    CONSTRAINT requests_request_book_id_fkey
        FOREIGN KEY (request_book_id)
        REFERENCES library.books(book_id),

    CONSTRAINT chk_request_status
        CHECK (
            request_status IN ('Active', 'Approved', 'Fulfilled', 'Cancelled')
        ),

    CONSTRAINT requests_request_status_check
        CHECK (
            request_status IN ('Active', 'Fulfilled', 'Cancelled')
        )
);

CREATE TABLE circulation.reservations (
    reservation_id SERIAL PRIMARY KEY,
    reservation_patron_id INTEGER NOT NULL,
    reservation_book_id INTEGER NOT NULL,
    reservation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    reservation_status VARCHAR(20) DEFAULT 'Active',

    CONSTRAINT reservations_reservation_patron_id_fkey
        FOREIGN KEY (reservation_patron_id)
        REFERENCES members.patrons(patron_id),

    CONSTRAINT reservations_reservation_book_id_fkey
        FOREIGN KEY (reservation_book_id)
        REFERENCES library.books(book_id),

    CONSTRAINT reservations_reservation_status_check
        CHECK (
            reservation_status IN ('Active', 'Fulfilled', 'Cancelled')
        )
);

CREATE TABLE circulation.hold (
    hold_id SERIAL PRIMARY KEY,
    hold_patron_id INTEGER NOT NULL,
    hold_book_id INTEGER NOT NULL,
    hold_date DATE NOT NULL DEFAULT CURRENT_DATE,
    hold_status VARCHAR(20) DEFAULT 'Active',

    CONSTRAINT hold_hold_patron_id_fkey
        FOREIGN KEY (hold_patron_id)
        REFERENCES members.patrons(patron_id),

    CONSTRAINT hold_hold_book_id_fkey
        FOREIGN KEY (hold_book_id)
        REFERENCES library.books(book_id),

    CONSTRAINT hold_hold_status_check
        CHECK (hold_status IN ('Active', 'Fulfilled', 'Cancelled'))
);

-- =====================
-- content
-- =====================

CREATE TABLE content.news (
    news_id SERIAL PRIMARY KEY,
    news_title TEXT NOT NULL,
    news_category VARCHAR(100) DEFAULT 'Announcements',
    news_content TEXT NOT NULL,
    news_excerpt TEXT,
    news_author VARCHAR(100) DEFAULT 'Library Team',
    news_status VARCHAR(20) DEFAULT 'Draft',
    news_featured BOOLEAN DEFAULT FALSE,
    news_image_url TEXT,
    news_created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    news_published_at DATE,

    CONSTRAINT news_news_status_check
        CHECK (news_status IN ('Draft', 'Published'))
);

CREATE TABLE content.events (
    event_id SERIAL PRIMARY KEY,
    event_title VARCHAR(100) NOT NULL,
    event_description TEXT NOT NULL,
    event_start_date DATE NOT NULL,
    event_end_date DATE,
    event_start_time TIME WITHOUT TIME ZONE NOT NULL,
    event_end_time TIME WITHOUT TIME ZONE,
    event_venue VARCHAR(50),
    event_image TEXT,
    event_status VARCHAR(50) NOT NULL DEFAULT 'Draft',
    event_registration_required BOOLEAN NOT NULL DEFAULT FALSE,
    event_category VARCHAR(255)
);

CREATE TABLE content.event_photos (
    photo_id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    photo_url TEXT NOT NULL,

    CONSTRAINT event_photos_event_id_fkey
        FOREIGN KEY (event_id)
        REFERENCES content.events(event_id)
);