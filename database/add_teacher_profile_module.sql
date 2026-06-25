-- Teacher Profile Module schema
-- Safe to run multiple times.

ALTER TABLE users ADD COLUMN IF NOT EXISTS photo VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS kurdish_full_name VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS date_of_birth DATE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS personal_email VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS staff_id VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS college VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS academic_title VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS qualification VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS position VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS status VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS general_specialization VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS specific_specialization VARCHAR(150);
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(30);
ALTER TABLE users ADD COLUMN IF NOT EXISTS biography TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS cv VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_staff_id
ON users(staff_id)
WHERE staff_id IS NOT NULL AND staff_id <> '';

CREATE TABLE IF NOT EXISTS teacher_phones (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    phone_number VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teacher_social_media (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    social_type VARCHAR(100) NOT NULL,
    link VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teacher_languages (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scientific_titles (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    scientific_title VARCHAR(150) NOT NULL,
    university VARCHAR(150) NOT NULL,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seminars (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    present_type VARCHAR(50) NOT NULL,
    number_of_attend INTEGER,
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workshops (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    present_national VARCHAR(255),
    present_international VARCHAR(255),
    number_of_attend INTEGER,
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conferences (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    link VARCHAR(500),
    place VARCHAR(150),
    country VARCHAR(150),
    participation_type VARCHAR(150),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trainings (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    place VARCHAR(150),
    participation_type VARCHAR(150),
    level VARCHAR(50),
    start_date DATE,
    end_date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS committees (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    level VARCHAR(100),
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS research_evaluations (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_source VARCHAR(255) NOT NULL,
    level VARCHAR(50),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    activity_type VARCHAR(100),
    link VARCHAR(500),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluation_committees (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    department VARCHAR(150) NOT NULL,
    degree VARCHAR(100),
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teachings (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject VARCHAR(255) NOT NULL,
    department VARCHAR(150),
    number_of_hours INTEGER,
    level VARCHAR(50),
    stage VARCHAR(50),
    link VARCHAR(500),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS supervisions (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    research_title VARCHAR(255) NOT NULL,
    department VARCHAR(150),
    degree_type VARCHAR(100),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS acknowledgements (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_source VARCHAR(150) NOT NULL,
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memberships (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_name VARCHAR(255) NOT NULL,
    link VARCHAR(500),
    level VARCHAR(50),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS researches (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    publication_status VARCHAR(50),
    publication_type VARCHAR(100),
    journal_name_and_number VARCHAR(255),
    published_research_link VARCHAR(500),
    doi_link VARCHAR(500),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS books (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    publisher VARCHAR(255),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grants (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    grant_type VARCHAR(150),
    achievement VARCHAR(255),
    date DATE,
    attachment VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_teacher_phones_teacher ON teacher_phones(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_social_media_teacher ON teacher_social_media(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_languages_teacher ON teacher_languages(teacher_id);
CREATE INDEX IF NOT EXISTS idx_scientific_titles_teacher ON scientific_titles(teacher_id);
CREATE INDEX IF NOT EXISTS idx_seminars_teacher ON seminars(teacher_id);
CREATE INDEX IF NOT EXISTS idx_workshops_teacher ON workshops(teacher_id);
CREATE INDEX IF NOT EXISTS idx_conferences_teacher ON conferences(teacher_id);
CREATE INDEX IF NOT EXISTS idx_trainings_teacher ON trainings(teacher_id);
CREATE INDEX IF NOT EXISTS idx_committees_teacher ON committees(teacher_id);
CREATE INDEX IF NOT EXISTS idx_research_evaluations_teacher ON research_evaluations(teacher_id);
CREATE INDEX IF NOT EXISTS idx_activities_teacher ON activities(teacher_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_committees_teacher ON evaluation_committees(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teachings_teacher ON teachings(teacher_id);
CREATE INDEX IF NOT EXISTS idx_supervisions_teacher ON supervisions(teacher_id);
CREATE INDEX IF NOT EXISTS idx_acknowledgements_teacher ON acknowledgements(teacher_id);
CREATE INDEX IF NOT EXISTS idx_memberships_teacher ON memberships(teacher_id);
CREATE INDEX IF NOT EXISTS idx_researches_teacher ON researches(teacher_id);
CREATE INDEX IF NOT EXISTS idx_books_teacher ON books(teacher_id);
CREATE INDEX IF NOT EXISTS idx_grants_teacher ON grants(teacher_id);
