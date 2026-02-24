-- Create enrollment periods table
-- Admins can set specific time windows when students can enroll/unenroll

CREATE TABLE IF NOT EXISTS enrollment_periods (
    id SERIAL PRIMARY KEY,
    semester INTEGER NOT NULL, -- 1, 2, 3, or 4
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure valid date range
    CHECK (end_date > start_date)
);

-- Create index for efficient period lookup
CREATE INDEX IF NOT EXISTS idx_enrollment_periods_semester ON enrollment_periods(semester);
CREATE INDEX IF NOT EXISTS idx_enrollment_periods_dates ON enrollment_periods(start_date, end_date);

-- Function to check if enrollment is currently active for a semester
CREATE OR REPLACE FUNCTION is_enrollment_active(sem INTEGER) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM enrollment_periods
        WHERE semester = sem
        AND CURRENT_TIMESTAMP BETWEEN start_date AND end_date
    );
END;
$$ LANGUAGE plpgsql;
