import { NextRequest, NextResponse } from "next/server";
import { DELIVERY_BEATS, HUBS, POST_OFFICES } from "@/app/lib/postal-store";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const pin = (body.pin_code || "").trim();

    // Match post office by PIN or default to Ambattur H.O
    let office = POST_OFFICES.find((po) => po.pin_code === pin);
    if (!office) {
      office = POST_OFFICES[0];
    }

    const hub = HUBS.find((h) => h.code === office?.hub_code) || HUBS[0];
    const officeBeats = DELIVERY_BEATS.filter((b) => b.post_office_id === office?.id);
    const beats = officeBeats.length > 0 ? officeBeats : [DELIVERY_BEATS[0]];

    return NextResponse.json({
      post_office_name: office.name,
      pin_code: office.pin_code,
      district: office.district,
      primary_hub: hub,
      route_code: `RT-${hub.code.split("-")[1] || "MAA"}-${office.pin_code.slice(-3)}`,
      transport_mode: "Mechanized Departmental Postal Van",
      distance_km: 18.5,
      estimated_transit_hours: 1.25,
      dispatch_schedule: "Twice daily: 05:30 hrs & 14:00 hrs IST",
      beats: beats.map((b) => ({
        id: b.id,
        beat_number: b.beat_number,
        beat_name: b.beat_name,
        postman_name: b.postman_name,
        areas_covered: b.areas_covered,
      })),
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || "Route identification failed" }, { status: 500 });
  }
}
