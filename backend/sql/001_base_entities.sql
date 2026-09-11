-- =========================================================
-- 001: Base Postal Entities (Post Offices, Localities, Aliases,
--      Human Corrections) + PostGIS / pgvector extensions.
--
-- Run this BEFORE 002_ai_security_and_analysis.sql and
-- 003_hubs_routes_parcels_and_datasets.sql when applying the
-- SQL migrations directly (without the ORM create_all path).
-- =========================================================

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. Post Offices (Delivery Offices)
CREATE TABLE IF NOT EXISTS post_offices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(160) NOT NULL,
    pin_code varchar(6) NOT NULL,
    district varchar(120) NOT NULL,
    state varchar(120) NOT NULL,
    location geography(POINT, 4326),
    embedding vector(768),
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_post_office_identity UNIQUE (name, pin_code, district, state)
);

-- 2. Localities (Areas / Sub-Areas mapped to Post Offices)
CREATE TABLE IF NOT EXISTS localities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name varchar(160) NOT NULL,
    district varchar(120) NOT NULL,
    state varchar(120) NOT NULL,
    pin_code varchar(6),
    post_office_id uuid REFERENCES post_offices(id) ON DELETE SET NULL,
    location geography(POINT, 4326),
    embedding vector(768),
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT uq_locality_identity UNIQUE (name, pin_code, district, state)
);

-- 3. Vernacular / Colonial Locality Aliases
CREATE TABLE IF NOT EXISTS locality_aliases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    locality_id uuid NOT NULL REFERENCES localities(id) ON DELETE CASCADE,
    alias varchar(160) NOT NULL,
    language varchar(16),
    CONSTRAINT uq_locality_alias UNIQUE (locality_id, alias)
);

-- 4. Human-in-the-Loop Operator Corrections
CREATE TABLE IF NOT EXISTS human_corrections (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    input_address text NOT NULL,
    predicted_post_office_id uuid REFERENCES post_offices(id) ON DELETE SET NULL,
    corrected_post_office_id uuid REFERENCES post_offices(id) ON DELETE SET NULL,
    correction_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for Query Performance
CREATE INDEX IF NOT EXISTS ix_post_offices_name ON post_offices(name);
CREATE INDEX IF NOT EXISTS ix_post_offices_pin_code ON post_offices(pin_code);
CREATE INDEX IF NOT EXISTS ix_post_offices_district ON post_offices(district);
CREATE INDEX IF NOT EXISTS ix_post_offices_state ON post_offices(state);
CREATE INDEX IF NOT EXISTS ix_localities_name ON localities(name);
CREATE INDEX IF NOT EXISTS ix_localities_district ON localities(district);
CREATE INDEX IF NOT EXISTS ix_localities_state ON localities(state);
CREATE INDEX IF NOT EXISTS ix_localities_pin_code ON localities(pin_code);
CREATE INDEX IF NOT EXISTS ix_locality_aliases_locality ON locality_aliases(locality_id);
CREATE INDEX IF NOT EXISTS ix_locality_aliases_alias ON locality_aliases(alias);