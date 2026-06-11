-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Drop tables and types if they exist to ensure clean slate initialization
DROP TABLE IF EXISTS email_events CASCADE;
DROP TABLE IF EXISTS applications CASCADE;
DROP TABLE IF EXISTS matches CASCADE;
DROP TABLE IF EXISTS jobs CASCADE;
DROP TABLE IF EXISTS resumes CASCADE;
DROP TYPE IF EXISTS app_status CASCADE;

-- Enforce consistency on status flags
CREATE TYPE app_status AS ENUM ('saved', 'queued', 'reviewing', 'applied', 'interview', 'rejected', 'offer');

-- Resumes table (stores base resume)
CREATE TABLE resumes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_text TEXT NOT NULL,
  parsed_json JSONB NOT NULL, -- {skills: [], education: [], projects: [], experience: []}
  embedding vector(384),      -- 384-dimensional embedding from all-MiniLM-L6-v2
  uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Jobs table (scraped listings)
CREATE TABLE jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  company TEXT NOT NULL,
  description TEXT NOT NULL,
  location TEXT,
  source TEXT NOT NULL,
  url TEXT UNIQUE NOT NULL,
  embedding vector(384),      -- 384-dimensional embedding
  scraped_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Matches table
CREATE TABLE matches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
  score FLOAT NOT NULL,
  matched_skills TEXT[] NOT NULL,
  missing_skills TEXT[] NOT NULL,
  explanation TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  UNIQUE(job_id)
);

-- Applications table
CREATE TABLE applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
  status app_status NOT NULL DEFAULT 'saved',
  tailored_resume_url TEXT,
  cover_letter TEXT,
  applied_at TIMESTAMP WITH TIME ZONE,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
  UNIQUE(job_id)
);

-- Email events (automated response tracker)
CREATE TABLE email_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  detected_status app_status NOT NULL,
  received_at TIMESTAMP WITH TIME ZONE NOT NULL
);
