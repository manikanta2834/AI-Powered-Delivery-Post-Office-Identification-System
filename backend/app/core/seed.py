"""Authoritative Seed Master Data for Post Offices, Hubs, Routes, Delivery Beats, and Parcels."""

import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security_ext import hash_password
from app.models import (
    DeliveryBeat,
    Hub,
    Locality,
    LocalityAlias,
    Parcel,
    ParcelEvent,
    PostOffice,
    Route,
    SystemConfiguration,
    User,
)


async def seed_master_data(session: AsyncSession) -> None:
    """Populate database with authoritative postal seed entities idempotently."""
    # 1. Seed Default Users if none exist
    user_count = await session.scalar(select(User).limit(1))
    if user_count is None:
        citizen_user = User(
            email="citizen@indiapost.gov.in",
            full_name="Priya Sharma",
            password_hash=hash_password("Citizen@2026"),
            role="citizen",
            is_active=True,
        )
        operator_user = User(
            email="operator.raman@indiapost.gov.in",
            full_name="K. Raman (Sorting Operator #TN-402)",
            password_hash=hash_password("Operator@2026"),
            role="operator",
            is_active=True,
        )
        admin_user = User(
            email="admin.nair@indiapost.gov.in",
            full_name="Dr. S. Nair (Postal Superintendent / Admin)",
            password_hash=hash_password("Admin@2026"),
            role="admin",
            is_active=True,
        )
        session.add_all([citizen_user, operator_user, admin_user])
        await session.flush()

    # 2. Seed Hubs if none exist
    hub_count = await session.scalar(select(Hub).limit(1))
    if hub_count is None:
        hub_chennai_nsh = Hub(
            code="NSH-MAA",
            name="Chennai National Sorting Hub (NSH)",
            hub_type="NSH",
            circle="Tamil Nadu Circle",
            district="Chennai",
            state="Tamil Nadu",
            metadata_json={"capacity_bags_per_day": 45000, "sorting_lanes": 8},
        )
        hub_chennai_ich = Hub(
            code="ICH-MAA",
            name="Chennai Intra-Circle Hub (ICH)",
            hub_type="ICH",
            circle="Tamil Nadu Circle",
            district="Chennai",
            state="Tamil Nadu",
            metadata_json={"capacity_bags_per_day": 25000, "sorting_lanes": 4},
        )
        hub_blr_air = Hub(
            code="ASH-BLR",
            name="Bengaluru Air Sorting Hub (ASH)",
            hub_type="NSH",
            circle="Karnataka Circle",
            district="Bengaluru",
            state="Karnataka",
            metadata_json={"capacity_bags_per_day": 60000, "sorting_lanes": 12},
        )
        session.add_all([hub_chennai_nsh, hub_chennai_ich, hub_blr_air])
        await session.flush()
    else:
        hub_chennai_nsh = await session.scalar(select(Hub).where(Hub.code == "NSH-MAA").limit(1))
        hub_chennai_ich = await session.scalar(select(Hub).where(Hub.code == "ICH-MAA").limit(1))
        hub_blr_air = await session.scalar(select(Hub).where(Hub.code == "ASH-BLR").limit(1))

    # 3. Seed / Link Key Post Offices
    offices_data = [
        ("Ambattur H.O", "600053", "Chennai", "Tamil Nadu", "Head Post Office"),
        ("Anna Nagar H.O", "600040", "Chennai", "Tamil Nadu", "Head Post Office"),
        ("T.Nagar H.O", "600017", "Chennai", "Tamil Nadu", "Head Post Office"),
        ("Fort St.George S.O", "600009", "Chennai", "Tamil Nadu", "Sub Post Office"),
        ("Adyar H.O", "600020", "Chennai", "Tamil Nadu", "Head Post Office"),
        ("Mylapore H.O", "600004", "Chennai", "Tamil Nadu", "Head Post Office"),
        ("Koramangala VI Bk S.O", "560095", "Bengaluru", "Karnataka", "Sub Post Office"),
        ("Bengaluru GPO", "560001", "Bengaluru", "Karnataka", "General Post Office"),
    ]

    office_entities: dict[str, PostOffice] = {}
    for name, pin, dist, st, otype in offices_data:
        existing = await session.scalar(select(PostOffice).where(PostOffice.pin_code == pin).limit(1))
        if existing is not None:
            office_entities[name] = existing
        else:
            po = PostOffice(
                name=name,
                pin_code=pin,
                district=dist,
                state=st,
                metadata_json={"office_type": otype, "verified": True, "source": "seed_master"},
            )
            session.add(po)
            office_entities[name] = po
    await session.flush()

    # 4. Seed Localities & Aliases if missing
    localities_data = [
        ("Ambattur", "600053", "Chennai", "Tamil Nadu", "Ambattur H.O", ["Ambathur", "Ambattur OT", "Ambattur Ind Estate"]),
        ("Anna Nagar", "600040", "Chennai", "Tamil Nadu", "Anna Nagar H.O", ["Anna Nagar West", "Shanthi Colony"]),
        ("T.Nagar", "600017", "Chennai", "Tamil Nadu", "T.Nagar H.O", ["Thyagaraya Nagar", "Pondy Bazaar"]),
        ("Secretariat", "600009", "Chennai", "Tamil Nadu", "Fort St.George S.O", ["Madras Fort", "Fort St George"]),
        ("Adyar", "600020", "Chennai", "Tamil Nadu", "Adyar H.O", ["Adayar", "Gandhi Nagar"]),
        ("Mylapore", "600004", "Chennai", "Tamil Nadu", "Mylapore H.O", ["Kapaleeshwarar", "Luz"]),
        ("Koramangala", "560095", "Bengaluru", "Karnataka", "Koramangala VI Bk S.O", ["Koramangala 5th Block", "Sony Signal"]),
        ("Bengaluru GPO Area", "560001", "Bengaluru", "Karnataka", "Bengaluru GPO", ["Vidhana Soudha", "Cubbon Park"]),
    ]

    for loc_name, pin, dist, st, parent_office_name, aliases in localities_data:
        existing_loc = await session.scalar(select(Locality).where(Locality.name == loc_name, Locality.pin_code == pin).limit(1))
        if existing_loc is None:
            parent_po = office_entities.get(parent_office_name)
            loc = Locality(
                name=loc_name,
                pin_code=pin,
                district=dist,
                state=st,
                post_office_id=parent_po.id if parent_po else None,
                metadata_json={"verified": True},
            )
            session.add(loc)
            await session.flush()
            for al in aliases:
                session.add(LocalityAlias(locality_id=loc.id, alias=al, language="en"))
        else:
            alias_exists = await session.scalar(select(LocalityAlias).where(LocalityAlias.locality_id == existing_loc.id).limit(1))
            if alias_exists is None:
                for al in aliases:
                    session.add(LocalityAlias(locality_id=existing_loc.id, alias=al, language="en"))

    # 5. Seed Delivery Beats
    ambattur_po = office_entities.get("Ambattur H.O")
    beat4 = None
    beat1 = None
    if ambattur_po:
        beat4 = await session.scalar(select(DeliveryBeat).where(DeliveryBeat.post_office_id == ambattur_po.id, DeliveryBeat.beat_number == 4).limit(1))
        if beat4 is None:
            beat4 = DeliveryBeat(
                post_office_id=ambattur_po.id,
                beat_number=4,
                beat_name="Beat #4 (Industrial North)",
                postman_name="K. Murugan (Postman #402)",
                areas_covered="Ambattur Industrial Estate, SIDCO North Phase, SBI Complex",
            )
            session.add(beat4)

        beat1 = await session.scalar(select(DeliveryBeat).where(DeliveryBeat.post_office_id == ambattur_po.id, DeliveryBeat.beat_number == 1).limit(1))
        if beat1 is None:
            beat1 = DeliveryBeat(
                post_office_id=ambattur_po.id,
                beat_number=1,
                beat_name="Beat #1 (Ambattur OT / Old Town)",
                postman_name="M. Selvam (Postman #401)",
                areas_covered="Old Town Market, Gandhi Main Road",
            )
            session.add(beat1)
        await session.flush()
    tnagar_po = office_entities.get("T.Nagar H.O")
    beat7 = None
    if tnagar_po:
        beat7 = await session.scalar(select(DeliveryBeat).where(DeliveryBeat.post_office_id == tnagar_po.id, DeliveryBeat.beat_number == 7).limit(1))
        if beat7 is None:
            beat7 = DeliveryBeat(
                post_office_id=tnagar_po.id,
                beat_number=7,
                beat_name="Beat #7 (Commercial Hub)",
                postman_name="P. Venkatesh (Postman #701)",
                areas_covered="Pondy Bazaar, Panagal Park, Usman Road",
            )
            session.add(beat7)
            await session.flush()

    # 6. Seed Transit Routes if none exist
    route_count = await session.scalar(select(Route).limit(1))
    if route_count is None and hub_chennai_nsh and ambattur_po and tnagar_po:
        route_ambattur = Route(
            route_code="RT-MAA-AMB-04",
            origin_hub_id=hub_chennai_nsh.id,
            destination_office_id=ambattur_po.id,
            transport_mode="Road Express Van",
            distance_km=18.5,
            estimated_transit_hours=1.0,
            dispatch_schedule="05:15 AM & 13:30 PM Daily",
        )
        route_tnagar = Route(
            route_code="RT-MAA-TNG-02",
            origin_hub_id=hub_chennai_nsh.id,
            destination_office_id=tnagar_po.id,
            transport_mode="Road Carrier",
            distance_km=12.0,
            estimated_transit_hours=0.75,
            dispatch_schedule="06:00 AM & 14:00 PM Daily",
        )
        session.add_all([route_ambattur, route_tnagar])
        await session.flush()

    # 7. Seed Authentic Parcels & Detailed Event Timeline if none exist
    parcel_count = await session.scalar(select(Parcel).limit(1))
    if parcel_count is None and ambattur_po and tnagar_po and hub_chennai_nsh:
        now = datetime.now(timezone.utc)
        parcel_1 = Parcel(
            tracking_number="SP102938475IN",
            service_type="Speed Post Express",
            sender_name="E-Commerce Logistics Hub",
            sender_city="Bengaluru",
            sender_pin="560001",
            recipient_name="Priya Sharma",
            recipient_address="Ambattur near SBI bank, opp bus stand, Ambattur, Chennai",
            recipient_pin="600053",
            current_status="OUT_FOR_DELIVERY",
            assigned_office_id=ambattur_po.id,
            assigned_hub_id=hub_chennai_nsh.id,
            assigned_beat_id=beat4.id if beat4 else None,
            weight_kg=0.850,
            expected_delivery=now + timedelta(hours=4),
            rerouted=True,
            reroute_reason="Recipient PIN corrected automatically from 600001 to 600053 by AI Locality Engine.",
        )
        session.add(parcel_1)
        await session.flush()

        session.add_all([
            ParcelEvent(
                parcel_id=parcel_1.id,
                event_type="BOOKED",
                location_name="Bengaluru GPO (560001)",
                post_office_id=office_entities.get("Bengaluru GPO").id if office_entities.get("Bengaluru GPO") else None,
                status_description="Item Booked & AI Route Tagged",
                occurred_at=now - timedelta(hours=24),
            ),
            ParcelEvent(
                parcel_id=parcel_1.id,
                event_type="DISPATCHED",
                location_name="Bengaluru Air Sorting Hub (ASH)",
                hub_id=hub_blr_air.id if hub_blr_air else None,
                status_description="Air Mail Dispatched to Chennai NSH",
                occurred_at=now - timedelta(hours=18),
            ),
            ParcelEvent(
                parcel_id=parcel_1.id,
                event_type="RECEIVED_AT_HUB",
                location_name="Chennai National Sorting Hub (NSH)",
                hub_id=hub_chennai_nsh.id,
                status_description="Dispatched to Ambattur Delivery Post Office via Route RT-MAA-AMB-04",
                occurred_at=now - timedelta(hours=8),
            ),
            ParcelEvent(
                parcel_id=parcel_1.id,
                event_type="OUT_FOR_DELIVERY",
                location_name="Ambattur H.O (600053)",
                post_office_id=ambattur_po.id,
                status_description="Out for Delivery with Postman K. Murugan (Beat #4)",
                operator_notes="Item assigned to Beat #4 delivery bag",
                occurred_at=now - timedelta(minutes=45),
            ),
        ])

        parcel_2 = Parcel(
            tracking_number="EB982341902IN",
            service_type="Express Parcel",
            sender_name="Tamil Nadu Textbooks Corp",
            sender_city="Chennai",
            sender_pin="600009",
            recipient_name="Govt Hr Sec School",
            recipient_address="Pondy Bazaar, T.Nagar, Chennai",
            recipient_pin="600017",
            current_status="SORTED",
            assigned_office_id=tnagar_po.id,
            assigned_hub_id=hub_chennai_ich.id if hub_chennai_ich else None,
            assigned_beat_id=beat7.id if beat7 else None,
            weight_kg=4.200,
            expected_delivery=now + timedelta(days=1),
            rerouted=False,
        )
        session.add(parcel_2)
        await session.flush()

        session.add_all([
            ParcelEvent(
                parcel_id=parcel_2.id,
                event_type="BOOKED",
                location_name="Fort St.George S.O (600009)",
                post_office_id=office_entities.get("Fort St.George S.O").id if office_entities.get("Fort St.George S.O") else None,
                status_description="Item Picked Up & Manifested",
                occurred_at=now - timedelta(hours=10),
            ),
            ParcelEvent(
                parcel_id=parcel_2.id,
                event_type="SORTED",
                location_name="Chennai Intra-Circle Hub (ICH)",
                hub_id=hub_chennai_ich.id if hub_chennai_ich else None,
                status_description="Bag Sorted & Weighed (4.2 kg) for T.Nagar Delivery",
                occurred_at=now - timedelta(hours=3),
            ),
        ])

    # 8. Seed Default Scoring Weights Configuration if none exists
    config_count = await session.scalar(select(SystemConfiguration).limit(1))
    if config_count is None:
        session.add(
            SystemConfiguration(
                config_key="postal_scoring_weights",
                config_value={
                    "locality": 35.0,
                    "pin": 25.0,
                    "geospatial": 20.0,
                    "landmark": 10.0,
                    "historical": 10.0,
                },
            )
        )

    await session.commit()
