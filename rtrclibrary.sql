-- =====================
-- public (shared/config)
-- =====================
CREATE TABLE public.roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE public.app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- library
-- =====================
CREATE TABLE library.ddc_classifications (
    ddc_code CHARACTER VARYING(20) PRIMARY KEY
);

CREATE TABLE library.patron_categories (
    category_id SERIAL PRIMARY KEY,
    category_name VARCHAR(50) UNIQUE NOT NULL CHECK (category_name IN ('Primary Student','Secondary Student','TVET Student','Teacher','Community Member'))
);

CREATE TABLE library.books (
    book_id SERIAL PRIMARY KEY,
    book_account_number CHARACTER VARYING(20) NOT NULL,
    book_isbn CHARACTER VARYING(20) NOT NULL,
    book_title CHARACTER VARYING(255) NOT NULL,
    book_author TEXT[] NOT NULL,
    book_genre CHARACTER VARYING(255),
    book_language CHARACTER VARYING(50),
    book_publisher CHARACTER VARYING(255),
    book_publication_year CHARACTER VARYING(20),
    book_acquisition_method CHARACTER VARYING(50),
    book_shelf_location CHARACTER VARYING(100),
    book_condition CHARACTER VARYING(50),
    book_status CHARACTER VARYING(50) DEFAULT 'Available',
    book_acquisition_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    book_updation_date TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    book_ddc_code CHARACTER VARYING(20),
    CONSTRAINT fk_books_ddc FOREIGN KEY (book_ddc_code) REFERENCES library.ddc_classifications(ddc_code),
    CONSTRAINT books_acquisition_method_check CHECK (book_acquisition_method = ANY (ARRAY['Purchase','Donation','Exchange'])),
    CONSTRAINT books_status_check CHECK (book_status = ANY (ARRAY['Available','Issued','Reserved','Lost']))
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
    ebook_added_by VARCHAR(20),
    ebook_cover_url TEXT,
    ebook_subjects TEXT[],
    ebook_copyright BOOLEAN,
    ebook_added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- members
-- =====================
CREATE TABLE members.patrons (
    patron_id SERIAL PRIMARY KEY,
    patron_membership_number CHARACTER VARYING(20) NOT NULL,
    patron_name CHARACTER VARYING(50) NOT NULL,
    patron_gender CHARACTER VARYING(10),
    patron_date_of_birth DATE,
    patron_education_level CHARACTER VARYING(50),
    patron_locality TEXT,
    patron_password TEXT,
    patron_category_id INT REFERENCES library.patron_categories(category_id),
    CONSTRAINT patrons_gender_check CHECK (patron_gender = ANY (ARRAY['Male','Female','Other'])),
    CONSTRAINT patrons_education_level_check CHECK (patron_education_level = ANY (ARRAY['Primary','Secondary','Tertiary','Other']))
);

CREATE TABLE members.patron_contacts (
    contact_id SERIAL PRIMARY KEY,
    patron_id INT NOT NULL REFERENCES members.patrons(patron_id) ON DELETE CASCADE,
    contact_type VARCHAR(20) CHECK (contact_type IN ('Phone','Email','WhatsApp')),
    contact_value TEXT NOT NULL
);

CREATE TABLE members.users (
    user_id SERIAL PRIMARY KEY,
    user_patron_id INT UNIQUE REFERENCES members.patrons(patron_id) ON DELETE CASCADE,
    user_role_id INT NOT NULL DEFAULT 2 REFERENCES public.roles(role_id) ON UPDATE CASCADE,
    user_date_joined DATE NOT NULL DEFAULT CURRENT_DATE,
    user_status BOOLEAN NOT NULL DEFAULT TRUE,
    user_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    user_last_login TIMESTAMPTZ,
    user_created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    user_updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- circulation
-- =====================
CREATE TABLE circulation.borrowings (
    borrowing_id SERIAL PRIMARY KEY,
    borrowing_patron_id INT NOT NULL REFERENCES members.patrons(patron_id),
    borrowing_book_id INT NOT NULL REFERENCES library.books(book_id),
    borrowing_date DATE NOT NULL DEFAULT CURRENT_DATE,
    borrowing_due_date DATE NOT NULL,
    borrowing_return_date DATE,
    borrowing_status VARCHAR(20) DEFAULT 'Borrowed' CHECK (borrowing_status IN ('Borrowed','Returned','Overdue'))
);

CREATE TABLE circulation.borrowing_renewals (
    renewal_id SERIAL PRIMARY KEY,
    borrowing_id INT REFERENCES circulation.borrowings(borrowing_id),
    renewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_due_date DATE,
    new_due_date DATE
);

CREATE TABLE circulation.fines (
    fine_id SERIAL PRIMARY KEY,
    fine_borrowing_id INT NOT NULL REFERENCES circulation.borrowings(borrowing_id),
    fine_amount DECIMAL(10,2) NOT NULL,
    fine_paid BOOLEAN DEFAULT FALSE
);

CREATE TABLE circulation.requests (
    request_id SERIAL PRIMARY KEY,
    request_patron_id INT NOT NULL REFERENCES members.patrons(patron_id),
    request_book_id INT NOT NULL REFERENCES library.books(book_id),
    request_date DATE NOT NULL DEFAULT CURRENT_DATE,
    request_status VARCHAR(20) DEFAULT 'Active' CHECK (request_status IN ('Active','Approved','Fulfilled','Cancelled'))
);

CREATE TABLE circulation.reservations (
    reservation_id SERIAL PRIMARY KEY,
    reservation_patron_id INT NOT NULL REFERENCES members.patrons(patron_id),
    reservation_book_id INT NOT NULL REFERENCES library.books(book_id),
    reservation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    reservation_status VARCHAR(20) DEFAULT 'Active' CHECK (reservation_status IN ('Active','Fulfilled','Cancelled'))
);

CREATE TABLE circulation.hold (
    hold_id SERIAL PRIMARY KEY,
    hold_patron_id INT NOT NULL REFERENCES members.patrons(patron_id),
    hold_book_id INT NOT NULL REFERENCES library.books(book_id),
    hold_date DATE NOT NULL DEFAULT CURRENT_DATE,
    hold_status VARCHAR(20) DEFAULT 'Active' CHECK (hold_status IN ('Active','Fulfilled','Cancelled'))
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
    news_status VARCHAR(20) DEFAULT 'Draft' CHECK (news_status IN ('Draft','Published')),
    news_featured BOOLEAN DEFAULT FALSE,
    news_image_url TEXT,
    news_created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    news_published_at DATE
);

CREATE TABLE content.events (
    event_id SERIAL PRIMARY KEY,
    event_title VARCHAR(100) NOT NULL,
    event_category VARCHAR(100),
    event_description TEXT NOT NULL,
    event_start_date DATE NOT NULL,
    event_end_date DATE,
    event_start_time TIME NOT NULL,
    event_end_time TIME,
    event_venue VARCHAR(50),
    event_image TEXT,
    event_status VARCHAR(50) DEFAULT 'Draft' NOT NULL,
    event_registration_required BOOLEAN DEFAULT FALSE NOT NULL
);

CREATE TABLE content.event_photos (
    photo_id SERIAL PRIMARY KEY,
    event_id INT NOT NULL REFERENCES content.events(event_id) ON DELETE CASCADE,
    photo_url TEXT NOT NULL
);