-- Alter app_status enum to add needs_human and review_needed values
-- Note: ALTER TYPE ... ADD VALUE cannot be executed inside a transaction block in PostgreSQL.
-- This runs outside transactions due to run_migrations.py's autocommit=True connection setup.
ALTER TYPE app_status ADD VALUE IF NOT EXISTS 'needs_human';
ALTER TYPE app_status ADD VALUE IF NOT EXISTS 'review_needed';
