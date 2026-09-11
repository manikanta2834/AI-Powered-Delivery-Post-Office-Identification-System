import { NextRequest, NextResponse } from "next/server";
import { PARCELS } from "@/app/lib/postal-store";

export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const cleanId = (id || "").toUpperCase().trim();

  const parcel = PARCELS[cleanId];
  if (parcel) {
    return NextResponse.json(parcel);
  }

  // If not pre-seeded, dynamically generate realistic India Post consignment record
  const isSpeedPost = cleanId.startsWith("SP") || cleanId.startsWith("E");
  const dynamicParcel = {
    id: `par-${cleanId}`,
    tracking_number: cleanId,
    service_type: isSpeedPost ? "Speed Post Express" : "Registered Air Parcel",
    sender_name: "Central Dispatch Logistics",
    sender_city: "Bengaluru GPO",
    sender_pin: "560001",
    recipient_name: "Consignee Address Verification",
    recipient_address: "Ambattur Industrial Estate Phase II",
    recipient_pin: "600053",
    current_status: "Item In Transit at Sorting Hub",
    assigned_office_name: "Ambattur H.O (600053)",
    assigned_hub_name: "Chennai National Sorting Hub (NSH)",
    assigned_beat_name: "Beat #4 (Industrial North)",
    weight_kg: 0.85,
    expected_delivery: new Date(Date.now() + 18 * 3600 * 1000).toISOString(),
    rerouted: false,
    reroute_reason: null,
    events: [
      {
        id: `ev-${cleanId}-1`,
        event_type: "IN_TRANSIT",
        location_name: "Chennai National Sorting Hub (NSH)",
        status_description: "Consignment bagged and manifested for delivery post office dispatch",
        occurred_at: "Today, 07:15 AM",
      },
      {
        id: `ev-${cleanId}-2`,
        event_type: "ITEM_BOOKED",
        location_name: "Bengaluru GPO (560001)",
        status_description: "Article registered and AI barcoded at booking counter",
        occurred_at: "Yesterday, 03:40 PM",
      },
    ],
  };

  return NextResponse.json(dynamicParcel);
}
