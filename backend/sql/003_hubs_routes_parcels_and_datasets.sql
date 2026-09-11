-- =========================================================
-- 003: Hubs, Routes, Delivery Beats, Parcels, Tracking Events,
--      Dataset Ingestion Governance, and System Configurations
-- =========================================================

-- 1. Sorting Hubs (NSH, ICH, TMO)
CREATE TABLE IF NOT EXISTS hubs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code varchar(32) NOT NULL UNIQUE,
    name varchar(160) NOT NULL,
    hub_type varchar(32) NOT NULL DEFAULT 'NSH', -- NSH: National Sorting Hub, ICH: Intra-Circle Hub
    circle varchar(80) NOT NULL DEFAULT 'Tamil Nadu Circle',
    district varchar(120),
    state varchar(120) NOT NULL DEFAULT 'Tamil Nadu',
    is_active boolean NOT NULL DEFAULT true,
    metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 2. Delivery Beats within Post Offices
CREATE TABLE IF NOT EXISTS delivery_beats (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    post_office_id uuid NOT NULL REFERENCES post_offices(id) ON DELETE CASCADE,
    beat_number integer NOT NULL,
    beat_name varchar(160) NOT NULL,
    postman_name varchar(160),
    areas_covered text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (post_office_id, beat_number)
);

-- 3. Transit & Dispatch Routes
CREATE TABLE IF NOT EXISTS routes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    route_code varchar(48) NOT NULL UNIQUE,
    origin_hub_id uuid NOT NULL REFERENCES hubs(id) ON DELETE RESTRICT,
    destination_office_id uuid NOT NULL REFERENCES post_offices(id) ON DELETE RESTRICT,
    transport_mode varchar(32) NOT NULL DEFAULT 'Road', -- Road, Air, Rail
    distance_km numeric(8, 2) NOT NULL DEFAULT 0.0,
    estimated_transit_hours numeric(5, 2) NOT NULL DEFAULT 2.5,
    dispatch_schedule varchar(120) NOT NULL DEFAULT '05:30 AM / 14:00 PM Daily',
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 4. Parcels & Consignments
CREATE TABLE IF NOT EXISTS parcels (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tracking_number varchar(32) NOT NULL UNIQUE,
    service_type varchar(48) NOT NULL DEFAULT 'Speed Post Express',
    sender_name varchar(160) NOT NULL,
    sender_city varchar(120) NOT NULL,
    sender_pin varchar(6) NOT NULL,
    recipient_name varchar(160) NOT NULL,
    recipient_address text NOT NULL,
    recipient_pin varchar(6) NOT NULL,
    current_status varchar(48) NOT NULL DEFAULT 'BOOKED', -- BOOKED, IN_TRANSIT, SORTED, OUT_FOR_DELIVERY, DELIVERED
    assigned_office_id uuid REFERENCES post_offices(id) ON DELETE SET NULL,
    assigned_hub_id uuid REFERENCES hubs(id) ON DELETE SET NULL,
    assigned_beat_id uuid REFERENCES delivery_beats(id) ON DELETE SET NULL,
    weight_kg numeric(6, 3) NOT NULL DEFAULT 0.500,
    expected_delivery timestamptz,
    rerouted boolean NOT NULL DEFAULT false,
    reroute_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- 5. Parcel Tracking Scan Events (Immutable Log)
CREATE TABLE IF NOT EXISTS parcel_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    parcel_id uuid NOT NULL REFERENCES parcels(id) ON DELETE CASCADE,
    event_type varchar(48) NOT NULL, -- BOOKED, DISPATCHED, RECEIVED_AT_HUB, SORTED, OUT_FOR_DELIVERY, DELIVERED
    location_name varchar(160) NOT NULL,
    post_office_id uuid REFERENCES post_offices(id) ON DELETE SET NULL,
    hub_id uuid REFERENCES hubs(id) ON DELETE SET NULL,
    status_description text NOT NULL,
    operator_notes text,
    occurred_at timestamptz NOT NULL DEFAULT now()
);

-- 6. PIN Code Dataset Version Governance
CREATE TABLE IF NOT EXISTS dataset_versions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag varchar(48) NOT NULL UNIQUE,
    source_filename varchar(255) NOT NULL,
    sha256_checksum varchar(64) NOT NULL,
    total_records integer NOT NULL DEFAULT 0,
    valid_records integer NOT NULL DEFAULT 0,
    error_records integer NOT NULL DEFAULT 0,
    status varchar(32) NOT NULL DEFAULT 'STAGED', -- STAGED, APPROVED, REJECTED, ROLLED_BACK
    validation_report jsonb NOT NULL DEFAULT '{}'::jsonb,
    uploaded_by uuid REFERENCES users(id) ON DELETE SET NULL,
    approved_by uuid REFERENCES users(id) ON DELETE SET NULL,
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- 7. Staging Table for Ingestion Pipeline
CREATE TABLE IF NOT EXISTS dataset_staging_records (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_version_id uuid NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    row_index integer NOT NULL,
    city varchar(160),
    area varchar(160),
    pincode varchar(32),
    district varchar(120),
    state varchar(120),
    is_valid boolean NOT NULL DEFAULT true,
    validation_errors jsonb NOT NULL DEFAULT '[]'::jsonb
);

-- 8. System Configurations & Scoring Weights
CREATE TABLE IF NOT EXISTS system_configurations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key varchar(80) NOT NULL UNIQUE,
    config_value jsonb NOT NULL,
    updated_by uuid REFERENCES users(id) ON DELETE SET NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes for Query Performance
CREATE INDEX IF NOT EXISTS ix_hubs_code ON hubs(code);
CREATE INDEX IF NOT EXISTS ix_routes_hub_office ON routes(origin_hub_id, destination_office_id);
CREATE INDEX IF NOT EXISTS ix_parcels_tracking ON parcels(tracking_number);
CREATE INDEX IF NOT EXISTS ix_parcels_status ON parcels(current_status);
CREATE INDEX IF NOT EXISTS ix_parcel_events_parcel ON parcel_events(parcel_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_dataset_versions_tag ON dataset_versions(version_tag);
CREATE INDEX IF NOT EXISTS ix_dataset_staging_version ON dataset_staging_records(dataset_version_id);
