"""Unit tests for Pydantic request and response schemas."""

import pytest
from pydantic import ValidationError
from app.api.schemas import (
    AddressAnalysisRequest,
    CandidateResponse,
    LoginRequest,
    MfaVerifyRequest,
    RouteIdentifyRequest,
    WeightsUpdatePayload,
)


def test_address_analysis_request_validation():
    req = AddressAnalysisRequest(address="Ambattur H.O, Chennai 600053", language_hint="English")
    assert req.address == "Ambattur H.O, Chennai 600053"

    with pytest.raises(ValidationError):
        AddressAnalysisRequest(address="")


def test_weights_payload_validation():
    # Sum must be 100
    w = WeightsUpdatePayload(locality=35, pin=25, geospatial=20, landmark=10, historical=10)
    assert w.locality == 35

    with pytest.raises(ValidationError):
        WeightsUpdatePayload(locality=100, pin=50, geospatial=20, landmark=10, historical=10)


def test_login_request_validation():
    req = LoginRequest(email="operator.raman@indiapost.gov.in", password="ValidPassword123")
    assert req.email == "operator.raman@indiapost.gov.in"

    with pytest.raises(ValidationError):
        LoginRequest(email="", password="")


def test_mfa_verify_request_validation():
    req = MfaVerifyRequest(email="operator.raman@indiapost.gov.in", totp_code="123456")
    assert req.email == "operator.raman@indiapost.gov.in"
    assert req.totp_code == "123456"

    with pytest.raises(ValidationError):
        MfaVerifyRequest(email="invalid", totp_code="123")
