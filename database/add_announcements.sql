-- System-wide announcements for teacher profile dashboard.

CREATE TABLE IF NOT EXISTS announcements (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at DATE DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_announcements_active_date
ON announcements(is_active, published_at DESC, id DESC);
