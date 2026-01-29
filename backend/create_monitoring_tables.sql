-- Migration: Create monitoring system tables
-- Run this with: psql -U postgres -d postgres -f create_monitoring_tables.sql
-- Or via Docker: docker exec -i sentinel-postgres psql -U postgres -d postgres < create_monitoring_tables.sql

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
DO $$ BEGIN
    CREATE TYPE monitoring_mode AS ENUM ('PASSIVE', 'ACTIVE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('active', 'completed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE event_type AS ENUM ('motion', 'person', 'vehicle', 'animal', 'package', 'unknown');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE severity AS ENUM ('low', 'medium', 'high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Table: monitoring_jobs
CREATE TABLE IF NOT EXISTS monitoring_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    chat_id UUID,
    mode monitoring_mode NOT NULL DEFAULT 'PASSIVE',
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ends_at TIMESTAMP,
    status job_status NOT NULL DEFAULT 'active',
    config JSONB,
    
    -- Indexes
    CONSTRAINT monitoring_jobs_user_id_idx CHECK (user_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_monitoring_jobs_user_id ON monitoring_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_jobs_status ON monitoring_jobs(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_jobs_started_at ON monitoring_jobs(started_at DESC);

COMMENT ON TABLE monitoring_jobs IS 'Tracks monitoring sessions (PASSIVE and ACTIVE modes)';
COMMENT ON COLUMN monitoring_jobs.ends_at IS 'For timed monitoring (e.g., monitor for 15 minutes)';
COMMENT ON COLUMN monitoring_jobs.config IS 'Camera settings, detection thresholds, device IDs, etc.';

-- Table: monitoring_events
CREATE TABLE IF NOT EXISTS monitoring_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    event_type event_type NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    severity severity NOT NULL DEFAULT 'low',
    metadata JSONB,
    
    -- No FK constraint for performance (high-frequency writes)
    CONSTRAINT monitoring_events_job_id_idx CHECK (job_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_monitoring_events_job_id ON monitoring_events(job_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_events_timestamp ON monitoring_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_monitoring_events_event_type ON monitoring_events(event_type);

COMMENT ON TABLE monitoring_events IS 'Raw detection events from vision model (high-frequency writes)';
COMMENT ON COLUMN monitoring_events.confidence IS 'Model confidence score (0.0 - 1.0)';
COMMENT ON COLUMN monitoring_events.metadata IS 'bbox, frame_url, device_id, clip_path, etc.';

-- Table: monitoring_alerts
CREATE TABLE IF NOT EXISTS monitoring_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL,
    event_ids UUID[] NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    alert_type event_type NOT NULL,
    message TEXT NOT NULL,
    severity severity NOT NULL,
    acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    chat_id UUID,
    metadata JSONB,
    
    CONSTRAINT monitoring_alerts_job_id_idx CHECK (job_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_job_id ON monitoring_alerts(job_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_timestamp ON monitoring_alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_acknowledged ON monitoring_alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_severity ON monitoring_alerts(severity);

COMMENT ON TABLE monitoring_alerts IS 'User-facing alerts (deduplicated from events, created only in ACTIVE mode)';
COMMENT ON COLUMN monitoring_alerts.event_ids IS 'Source event IDs that triggered this alert';
COMMENT ON COLUMN monitoring_alerts.chat_id IS 'Chat thread where alert was sent (if any)';
COMMENT ON COLUMN monitoring_alerts.metadata IS 'Frame URLs, clip URLs, detection details, etc.';

-- Verification queries
SELECT 'Monitoring tables created successfully!' AS status;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE 'monitoring_%'
ORDER BY table_name;