-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
  id UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000000'::uuid,
  keywords TEXT NOT NULL DEFAULT 'AI Engineer',
  location TEXT NOT NULL DEFAULT '',
  limit_count INTEGER NOT NULL DEFAULT 5,
  threshold FLOAT NOT NULL DEFAULT 0.8,
  internshala_email TEXT DEFAULT '',
  internshala_password TEXT DEFAULT '',
  gmail_email TEXT DEFAULT '',
  gmail_app_password TEXT DEFAULT '',
  schedule_interval_hours INTEGER NOT NULL DEFAULT 12,
  is_schedule_enabled BOOLEAN NOT NULL DEFAULT true,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Seed default settings if not exists
INSERT INTO system_settings (id, keywords, location, limit_count, threshold)
VALUES ('00000000-0000-0000-0000-000000000000'::uuid, 'AI Engineer', '', 5, 0.8)
ON CONFLICT (id) DO NOTHING;
