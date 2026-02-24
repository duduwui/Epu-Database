-- Add file support to homework table
ALTER TABLE homework
ADD COLUMN filename VARCHAR(255),
ADD COLUMN file_path VARCHAR(500),
ADD COLUMN file_type VARCHAR(50),
ADD COLUMN file_size INTEGER;
