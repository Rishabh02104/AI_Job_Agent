-- Add Simplify Copilot fields to system_settings
ALTER TABLE system_settings 
ADD COLUMN IF NOT EXISTS github_url TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS linkedin_url TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS portfolio_url TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS requires_sponsorship BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS authorized_to_work BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS notice_period_days INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS salary_expectations TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS gender TEXT DEFAULT 'Decline to self-identify',
ADD COLUMN IF NOT EXISTS race TEXT DEFAULT 'Decline to self-identify',
ADD COLUMN IF NOT EXISTS disability_status TEXT DEFAULT 'Decline to self-identify',
ADD COLUMN IF NOT EXISTS veteran_status TEXT DEFAULT 'Decline to self-identify';
