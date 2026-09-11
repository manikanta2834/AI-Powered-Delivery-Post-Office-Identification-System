import { NextRequest, NextResponse } from "next/server";
import {
  POST_OFFICES,
  LOCALITIES,
  HUBS,
  DELIVERY_BEATS,
  PARCELS,
  POSTAL_DATASET_INFO,
} from "@/app/lib/postal-store";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const type = searchParams.get("type") || "summary";
  const query = (searchParams.get("q") || "").toLowerCase().trim();
  const circle = (searchParams.get("circle") || "").toLowerCase().trim();

  if (type === "post_offices") {
    let results = POST_OFFICES;
    if (circle) {
      results = results.filter((po) => po.circle.toLowerCase().includes(circle));
    }
    if (query) {
      results = results.filter(
        (po) =>
          po.name.toLowerCase().includes(query) ||
          po.pin_code.includes(query) ||
          po.district.toLowerCase().includes(query) ||
          po.aliases.some((a) => a.toLowerCase().includes(query))
      );
    }
    return NextResponse.json({
      total: results.length,
      post_offices: results,
    });
  }

  if (type === "localities") {
    let results = LOCALITIES;
    if (circle) {
      results = results.filter((loc) => loc.circle.toLowerCase().includes(circle));
    }
    if (query) {
      results = results.filter(
        (loc) =>
          loc.name.toLowerCase().includes(query) ||
          loc.pin_code.includes(query) ||
          loc.district.toLowerCase().includes(query) ||
          loc.aliases.some((a) => a.toLowerCase().includes(query))
      );
    }
    return NextResponse.json({
      total: results.length,
      localities: results,
    });
  }

  if (type === "hubs") {
    return NextResponse.json({
      total: HUBS.length,
      hubs: HUBS,
    });
  }

  if (type === "beats") {
    return NextResponse.json({
      total: DELIVERY_BEATS.length,
      delivery_beats: DELIVERY_BEATS,
    });
  }

  if (type === "parcels") {
    return NextResponse.json({
      total: Object.keys(PARCELS).length,
      parcels: Object.values(PARCELS),
    });
  }

  // Circles breakdown
  const circleCounts: Record<string, { offices: number; localities: number }> = {};
  for (const po of POST_OFFICES) {
    if (!circleCounts[po.circle]) {
      circleCounts[po.circle] = { offices: 0, localities: 0 };
    }
    circleCounts[po.circle].offices += 1;
  }
  for (const loc of LOCALITIES) {
    if (circleCounts[loc.circle]) {
      circleCounts[loc.circle].localities += 1;
    }
  }

  return NextResponse.json({
    dataset_metadata: POSTAL_DATASET_INFO,
    counts: {
      post_offices: POST_OFFICES.length,
      localities: LOCALITIES.length,
      sorting_hubs: HUBS.length,
      delivery_beats: DELIVERY_BEATS.length,
      active_parcels: Object.keys(PARCELS).length,
    },
    circles: circleCounts,
    last_synced: new Date().toISOString(),
  });
}
