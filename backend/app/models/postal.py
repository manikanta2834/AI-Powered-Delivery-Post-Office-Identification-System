import uuid
from datetime import datetime

from geoalchemy2 import Geography
from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, false, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class PostOffice(Base):
    __tablename__ = "post_offices"
    __table_args__ = (UniqueConstraint("name", "pin_code", "district", "state", name="uq_post_office_identity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    pin_code: Mapped[str] = mapped_column(String(6), index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(120), index=True)
    location: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    localities: Mapped[list["Locality"]] = relationship(back_populates="post_office")


class Locality(Base):
    __tablename__ = "localities"
    __table_args__ = (UniqueConstraint("name", "pin_code", "district", "state", name="uq_locality_identity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(120), index=True)
    pin_code: Mapped[str | None] = mapped_column(String(6), index=True)
    post_office_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="SET NULL")
    )
    location: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(768))
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)

    post_office: Mapped[PostOffice | None] = relationship(back_populates="localities")
    aliases: Mapped[list["LocalityAlias"]] = relationship(back_populates="locality")


class LocalityAlias(Base):
    __tablename__ = "locality_aliases"
    __table_args__ = (UniqueConstraint("locality_id", "alias", name="uq_locality_alias"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locality_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("localities.id", ondelete="CASCADE"), index=True
    )
    alias: Mapped[str] = mapped_column(String(160), index=True)
    language: Mapped[str | None] = mapped_column(String(16))

    locality: Mapped[Locality] = relationship(back_populates="aliases")


class HumanCorrection(Base):
    __tablename__ = "human_corrections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_address: Mapped[str] = mapped_column(Text)
    predicted_post_office_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="SET NULL")
    )
    corrected_post_office_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="SET NULL")
    )
    correction_payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="operator", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(120))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AddressAnalysis(Base):
    __tablename__ = "address_analyses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    raw_address: Mapped[str] = mapped_column(Text)
    normalized_address: Mapped[str | None] = mapped_column(Text)
    detected_language: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    conflict_flags: Mapped[list] = mapped_column(JSONB, default=list)
    confidence_score: Mapped[int | None] = mapped_column(Integer)
    processing_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class AnalysisCandidate(Base):
    __tablename__ = "analysis_candidates"
    __table_args__ = (UniqueConstraint("analysis_id", "rank", name="uq_analysis_candidate_rank"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("address_analyses.id", ondelete="CASCADE"), index=True
    )
    post_office_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="RESTRICT"), index=True
    )
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[dict] = mapped_column(JSONB, default=dict)


class Hub(Base):
    __tablename__ = "hubs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    hub_type: Mapped[str] = mapped_column(String(32), default="NSH")  # NSH, ICH, TMO
    circle: Mapped[str] = mapped_column(String(80), default="Tamil Nadu Circle")
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(120), default="Tamil Nadu")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DeliveryBeat(Base):
    __tablename__ = "delivery_beats"
    __table_args__ = (UniqueConstraint("post_office_id", "beat_number", name="uq_post_office_beat"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_office_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="CASCADE"), index=True
    )
    beat_number: Mapped[int] = mapped_column(Integer)
    beat_name: Mapped[str] = mapped_column(String(160))
    postman_name: Mapped[str | None] = mapped_column(String(160))
    areas_covered: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    route_code: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    origin_hub_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hubs.id", ondelete="RESTRICT"), index=True
    )
    destination_office_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="RESTRICT"), index=True
    )
    transport_mode: Mapped[str] = mapped_column(String(32), default="Road")
    distance_km: Mapped[float] = mapped_column(Numeric(8, 2), default=0.0)
    estimated_transit_hours: Mapped[float] = mapped_column(Numeric(5, 2), default=2.5)
    dispatch_schedule: Mapped[str] = mapped_column(String(120), default="05:30 AM / 14:00 PM Daily")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracking_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    service_type: Mapped[str] = mapped_column(String(48), default="Speed Post Express")
    sender_name: Mapped[str] = mapped_column(String(160))
    sender_city: Mapped[str] = mapped_column(String(120))
    sender_pin: Mapped[str] = mapped_column(String(6))
    recipient_name: Mapped[str] = mapped_column(String(160))
    recipient_address: Mapped[str] = mapped_column(Text)
    recipient_pin: Mapped[str] = mapped_column(String(6))
    current_status: Mapped[str] = mapped_column(String(48), default="BOOKED", index=True)
    assigned_office_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="SET NULL")
    )
    assigned_hub_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hubs.id", ondelete="SET NULL")
    )
    assigned_beat_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("delivery_beats.id", ondelete="SET NULL")
    )
    weight_kg: Mapped[float] = mapped_column(Numeric(6, 3), default=0.500)
    expected_delivery: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rerouted: Mapped[bool] = mapped_column(Boolean, default=false)
    reroute_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ParcelEvent(Base):
    __tablename__ = "parcel_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parcels.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(48))  # BOOKED, DISPATCHED, RECEIVED_AT_HUB, SORTED, OUT_FOR_DELIVERY, DELIVERED
    location_name: Mapped[str] = mapped_column(String(160))
    post_office_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("post_offices.id", ondelete="SET NULL")
    )
    hub_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hubs.id", ondelete="SET NULL")
    )
    status_description: Mapped[str] = mapped_column(Text)
    operator_notes: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_tag: Mapped[str] = mapped_column(String(48), unique=True, index=True)
    source_filename: Mapped[str] = mapped_column(String(255))
    sha256_checksum: Mapped[str] = mapped_column(String(64))
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    valid_records: Mapped[int] = mapped_column(Integer, default=0)
    error_records: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="STAGED", index=True)  # STAGED, APPROVED, REJECTED, ROLLED_BACK
    validation_report: Mapped[dict] = mapped_column(JSONB, default=dict)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetStagingRecord(Base):
    __tablename__ = "dataset_staging_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("dataset_versions.id", ondelete="CASCADE"), index=True
    )
    row_index: Mapped[int] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(160))
    area: Mapped[str | None] = mapped_column(String(160))
    pincode: Mapped[str | None] = mapped_column(String(32))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_errors: Mapped[list] = mapped_column(JSONB, default=list)


class SystemConfiguration(Base):
    __tablename__ = "system_configurations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    config_value: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
