from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


# --- Authentication Schemas ---

class SignupRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="citizen", pattern="^(citizen|operator|admin)$")


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=6, max_length=128)


class MfaVerifyRequest(BaseModel):
    email: str
    totp_code: str = Field(min_length=6, max_length=6)


class ReAuthRequest(BaseModel):
    password: str = Field(min_length=4)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse


# --- Postal Address Intelligence Schemas ---

class AddressAnalysisRequest(BaseModel):
    address: str = Field(min_length=3, max_length=4000)
    language_hint: str | None = Field(default=None, max_length=32)


class CandidateResponse(BaseModel):
    id: UUID | None = None
    rank: int
    score: int
    office_name: str
    pin_code: str
    district: str
    state: str
    explanation: dict


class AddressAnalysisResponse(BaseModel):
    analysis_id: UUID
    raw_address: str
    normalized_address: str
    detected_language: str
    conflict_flags: list[str]
    confidence_score: int | None
    extracted_entities: dict[str, str] | None = None
    candidates: list[CandidateResponse]


class PostOfficeSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    pin_code: str
    district: str
    state: str
    metadata_json: dict


class CorrectionRequest(BaseModel):
    corrected_post_office_id: UUID
    notes: str | None = Field(default=None, max_length=1000)


# --- Hub & Route Logistics Schemas ---

class HubResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    hub_type: str
    circle: str
    district: str | None
    state: str


class DeliveryBeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    beat_number: int
    beat_name: str
    postman_name: str | None
    areas_covered: str | None


class RouteIdentifyRequest(BaseModel):
    post_office_id: UUID | None = None
    pin_code: str | None = None


class RouteIdentifyResponse(BaseModel):
    post_office_name: str
    pin_code: str
    district: str
    primary_hub: HubResponse | None
    route_code: str
    transport_mode: str
    distance_km: float
    estimated_transit_hours: float
    dispatch_schedule: str
    beats: list[DeliveryBeatResponse]


# --- Parcel Tracking Schemas ---

class ParcelEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    location_name: str
    status_description: str
    operator_notes: str | None
    occurred_at: datetime


class ParcelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tracking_number: str
    service_type: str
    sender_name: str
    sender_city: str
    sender_pin: str
    recipient_name: str
    recipient_address: str
    recipient_pin: str
    current_status: str
    assigned_office_name: str | None = None
    assigned_hub_name: str | None = None
    assigned_beat_name: str | None = None
    weight_kg: float
    expected_delivery: datetime | None
    rerouted: bool
    reroute_reason: str | None
    events: list[ParcelEventResponse] = []


class AddParcelEventRequest(BaseModel):
    event_type: str
    location_name: str
    status_description: str
    operator_notes: str | None = None


# --- Dataset Governance & Admin Schemas ---

class DatasetVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version_tag: str
    source_filename: str
    sha256_checksum: str
    total_records: int
    valid_records: int
    error_records: int
    status: str
    validation_report: dict
    created_at: datetime
    approved_at: datetime | None


class WeightsUpdatePayload(BaseModel):
    locality: float = Field(..., ge=0, le=100)
    pin: float = Field(..., ge=0, le=100)
    geospatial: float = Field(..., ge=0, le=100)
    landmark: float = Field(..., ge=0, le=100)
    historical: float = Field(..., ge=0, le=100)

    @model_validator(mode="after")
    def _weights_sum_to_100(self) -> "WeightsUpdatePayload":
        total = self.locality + self.pin + self.geospatial + self.landmark + self.historical
        if round(total, 2) != 100.0:
            raise ValueError(f"Weight percentages must sum up exactly to 100% (Received: {total}%)")
        return self


class SystemAnalyticsResponse(BaseModel):
    total_analyses: int
    total_post_offices: int
    total_localities: int
    total_parcels: int
    active_hubs: int
    pin_conflict_rate_percent: float
    human_corrections_count: int
    average_confidence: float
    recent_verifications: list[dict]
    system_status: str


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action: str
    resource_type: str | None
    resource_id: str | None
    details: dict
    created_at: datetime
