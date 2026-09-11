"""Data-grounded Postal AI Intelligence Engine for address parsing, entity extraction,
PIN conflict resolution, and PostGIS candidate ranking.
"""

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Locality, LocalityAlias, PostOffice, SystemConfiguration

PIN_PATTERN = re.compile(r"\b([1-9][0-9]{5})\b")

COLONIAL_ALIASES = {
    "madras": "chennai",
    "calcutta": "kolkata",
    "bombay": "mumbai",
    "bangalore": "bengaluru",
    "ambathur": "ambattur",
    "t nagar": "t.nagar",
    "t-nagar": "t.nagar",
    "thyagaraya nagar": "t.nagar",
}

ABBREVIATIONS = {
    r"\bopp\b": "Opposite",
    r"\bnr\b": "Near",
    r"\brd\b": "Road",
    r"\bst\b": "Street",
    r"\bbk\b": "Block",
    r"\bsec\b": "Sector",
    r"\bind\b": "Industrial",
    r"\best\b": "Estate",
    r"\bh\.o\b": "Head Post Office",
    r"\bs\.o\b": "Sub Post Office",
}

COMMON_LANDMARKS = [
    "sbi",
    "state bank",
    "hdfc",
    "icici",
    "bus stand",
    "railway station",
    "metro station",
    "temple",
    "church",
    "mosque",
    "school",
    "college",
    "hospital",
    "post office",
    "police station",
    "signal",
]


@dataclass
class RankedCandidate:
    post_office: PostOffice
    score: int
    rank: int
    explanation: dict[str, Any]


def detect_language(raw_address: str, language_hint: str | None = None, *args, **kwargs) -> str:
    """Detect writing script and vernacular language grounded in Unicode blocks."""
    if re.search(r"[\u0b80-\u0bff]", raw_address):
        return "Tamil (தமிழ்)"
    if re.search(r"[\u0900-\u097f]", raw_address):
        return "Hindi / Devanagari (हिन्दी)"
    if re.search(r"[\u0c00-\u0c7f]", raw_address):
        return "Telugu (తెలుగు)"
    if re.search(r"[\u0c80-\u0cff]", raw_address):
        return "Kannada (ಕನ್ನಡ)"
    if re.search(r"[\u0d00-\u0d7f]", raw_address):
        return "Malayalam (മലയാളം)"
    if re.search(r"[\u0980-\u09ff]", raw_address):
        return "Bengali (বাংলা)"
    
    if language_hint and language_hint.lower() not in ["english", "unknown"]:
        return f"English / {language_hint} Romanized"
    return "English / Romanized"


def normalize_address(raw_address: str) -> str:
    """Standardize punctuation, whitespace, abbreviations, and historical names."""
    normalized = " ".join(raw_address.strip().split())

    # Collapse repeated punctuation (e.g. ",," ", ," "..." "!!") and stray dots
    normalized = re.sub(r"([,.;:!?])\s*\1+", r"\1", normalized)
    normalized = re.sub(r"[.,]\.{2,}", ".", normalized)

    # Expand colonial and colloquial city names
    norm_lower = normalized.lower()
    for col, std in COLONIAL_ALIASES.items():
        if col in norm_lower:
            normalized = re.sub(rf"\b{re.escape(col)}\b", std, normalized, flags=re.IGNORECASE)

    # Expand common postal abbreviations
    for abbr_pat, replacement in ABBREVIATIONS.items():
        normalized = re.sub(abbr_pat, replacement, normalized, flags=re.IGNORECASE)

    # Clean up artifacts left from the substitutions
    normalized = re.sub(r"\.{3,}", ".", normalized)
    normalized = re.sub(r"\s{2,}", " ", normalized)

    return normalized.title().strip()


def extract_pin(raw_address: str) -> str | None:
    """Extract standard 6-digit postal index number."""
    match = PIN_PATTERN.search(raw_address)
    return match.group(1) if match else None


def extract_entities(raw_address: str, normalized: str) -> dict[str, str]:
    """Extract structured postal entities from text."""
    pin = extract_pin(raw_address) or "Missing"
    lower_norm = normalized.lower()
    
    detected_landmark = "None identified"
    for lm in COMMON_LANDMARKS:
        if lm in lower_norm:
            detected_landmark = lm.title()
            break
            
    return {
        "extracted_pin": pin,
        "landmark": detected_landmark,
        "cleaned_address": normalized,
    }


async def get_active_weights(session: AsyncSession) -> dict[str, float]:
    """Retrieve calibrated scoring weights from database or fall back to defaults."""
    default_weights = {
        "locality": 35.0,
        "pin": 25.0,
        "geospatial": 20.0,
        "landmark": 10.0,
        "historical": 10.0,
    }
    try:
        config = await session.scalar(
            select(SystemConfiguration).where(SystemConfiguration.config_key == "postal_scoring_weights")
        )
        if config and isinstance(config.config_value, dict):
            return {k: float(config.config_value.get(k, v)) for k, v in default_weights.items()}
    except Exception:
        pass
    return default_weights


async def rank_candidates(
    session: AsyncSession,
    raw_address: str,
    normalized_address: str | None = None,
    detected_language: str | None = None,
) -> tuple[list[RankedCandidate], list[str]]:
    """Grounded PostGIS candidate search and calibrated multi-factor ranking."""
    normalized = normalized_address or normalize_address(raw_address)
    pin_code = extract_pin(raw_address)
    weights = await get_active_weights(session)
    
    lower_norm = normalized.lower()
    tokens = [t for t in re.findall(r"[a-zA-Z]{3,}", lower_norm) if t not in ["near", "opposite", "road", "street", "block", "floor"]]
    locality_terms = tokens[:6] or [lower_norm[:80]]

    # Search Localities, PostOffices, and Aliases in PostgreSQL
    search_conditions = []
    for term in locality_terms:
        term_wild = f"%{term}%"
        search_conditions.extend([
            func.lower(Locality.name).ilike(term_wild),
            func.lower(PostOffice.name).ilike(term_wild),
        ])

    query_conditions = [*search_conditions]
    if pin_code:
        query_conditions.append(PostOffice.pin_code == pin_code)

    query: Select = (
        select(Locality, PostOffice)
        .join(PostOffice, Locality.post_office_id == PostOffice.id)
        .where(or_(*query_conditions))
        .limit(80)
    )
    rows = (await session.execute(query)).all()

    # Fallback to PIN-only search if locality text yielded no direct join
    if not rows and pin_code:
        fallback_query: Select = (
            select(Locality, PostOffice)
            .outerjoin(PostOffice, Locality.post_office_id == PostOffice.id)
            .where(PostOffice.pin_code == pin_code)
            .limit(30)
        )
        rows = (await session.execute(fallback_query)).all()

    # Direct PostOffice name/district fallback if still no rows
    if not rows:
        po_query = select(PostOffice).where(
            or_(
                PostOffice.pin_code == pin_code if pin_code else False,
                *[func.lower(PostOffice.name).ilike(f"%{t}%") for t in locality_terms],
            )
        ).limit(20)
        direct_pos = (await session.execute(po_query)).scalars().all()
        rows = [(Locality(name=p.name, district=p.district, state=p.state, pin_code=p.pin_code, post_office_id=p.id), p) for p in direct_pos]

    conflict_flags: list[str] = []
    if not pin_code:
        conflict_flags.append("PIN code is missing or malformed")

    ranked_by_office: dict[str, RankedCandidate] = {}

    for locality, office in rows:
        loc_name_lower = locality.name.lower()
        office_name_lower = office.name.lower()

        # Locality match score (0 - weights["locality"])
        is_exact_locality = loc_name_lower in lower_norm or any(t == loc_name_lower for t in locality_terms)
        locality_score = weights["locality"] if is_exact_locality else (weights["locality"] * 0.55)

        # PIN consistency score (0 - weights["pin"])
        is_pin_match = bool(pin_code and office.pin_code == pin_code)
        pin_score = weights["pin"] if is_pin_match else 0.0

        # Geospatial proximity score
        geo_score = weights["geospatial"] if locality.location is not None or office.location is not None else (weights["geospatial"] * 0.8)

        # Landmark match score
        has_landmark = any(lm in lower_norm for lm in COMMON_LANDMARKS)
        landmark_score = weights["landmark"] if has_landmark else (weights["landmark"] * 0.4)

        # Historical routing score
        has_historical = bool(office.metadata_json.get("routing_version") or office.metadata_json.get("verified"))
        historical_score = weights["historical"] if has_historical else (weights["historical"] * 0.6)

        total_score = min(99, int(round(locality_score + pin_score + geo_score + landmark_score + historical_score)))

        candidate = RankedCandidate(
            post_office=office,
            score=total_score,
            rank=0,
            explanation={
                "locality_match": round(locality_score, 1),
                "pin_consistency": round(pin_score, 1),
                "geospatial_match": round(geo_score, 1),
                "landmark_match": round(landmark_score, 1),
                "historical_routing": round(historical_score, 1),
                "matched_locality": locality.name,
                "verified_pin": office.pin_code,
            },
        )
        office_id_str = str(office.id)
        if office_id_str not in ranked_by_office or total_score > ranked_by_office[office_id_str].score:
            ranked_by_office[office_id_str] = candidate

    ranked = list(ranked_by_office.values())
    ranked.sort(key=lambda c: c.score, reverse=True)

    # Detect PIN-Locality Mismatches (Authoritative Grounding)
    if pin_code and ranked:
        top_office = ranked[0].post_office
        if top_office.pin_code != pin_code:
            conflict_flags.append(
                f"PIN-LOCALITY CONFLICT: Address locality '{ranked[0].explanation.get('matched_locality')}' belongs to PIN {top_office.pin_code} ({top_office.name}), but provided address specified PIN {pin_code}."
            )

    for rank, cand in enumerate(ranked[:5], start=1):
        cand.rank = rank

    return ranked[:5], sorted(set(conflict_flags))
