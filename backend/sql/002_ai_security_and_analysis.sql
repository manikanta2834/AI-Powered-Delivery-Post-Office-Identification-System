CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email varchar(320) NOT NULL UNIQUE,
    full_name varchar(160) NOT NULL,
    password_hash varchar(255) NOT NULL,
    role varchar(32) NOT NULL DEFAULT 'operator',
    is_active boolean NOT NULL DEFAULT true,
    last_login_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash varchar(128) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    action varchar(80) NOT NULL,
    resource_type varchar(80),
    resource_id varchar(120),
    ip_address varchar(64),
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS address_analyses (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    raw_address text NOT NULL,
    normalized_address text,
    detected_language varchar(32),
    status varchar(32) NOT NULL DEFAULT 'completed',
    conflict_flags jsonb NOT NULL DEFAULT '[]'::jsonb,
    confidence_score integer,
    processing_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analysis_candidates (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id uuid NOT NULL REFERENCES address_analyses(id) ON DELETE CASCADE,
    post_office_id uuid NOT NULL REFERENCES post_offices(id) ON DELETE RESTRICT,
    rank integer NOT NULL,
    score integer NOT NULL,
    explanation jsonb NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (analysis_id, rank)
);

CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expiry ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS ix_audit_logs_user_created ON audit_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_address_analyses_user_created ON address_analyses(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analysis_candidates_analysis_rank ON analysis_candidates(analysis_id, rank);