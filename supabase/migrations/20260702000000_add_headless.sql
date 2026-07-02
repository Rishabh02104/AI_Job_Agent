-- Add run_headless and auto_apply fields to system_settings
ALTER TABLE system_settings 
ADD COLUMN IF NOT EXISTS run_headless BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS auto_apply BOOLEAN DEFAULT false;
