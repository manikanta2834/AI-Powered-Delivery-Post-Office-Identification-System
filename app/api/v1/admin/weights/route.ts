import { NextRequest, NextResponse } from "next/server";
import { SCORING_WEIGHTS, updateScoringWeights } from "@/app/lib/postal-store";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(SCORING_WEIGHTS);
}

export async function PUT(req: NextRequest) {
  try {
    const body = await req.json();
    const { locality, pin, geospatial, landmark, historical } = body;

    if (
      typeof locality !== "number" ||
      typeof pin !== "number" ||
      typeof geospatial !== "number" ||
      typeof landmark !== "number" ||
      typeof historical !== "number"
    ) {
      return NextResponse.json({ detail: "All 5 scoring weight factors must be numbers." }, { status: 400 });
    }

    updateScoringWeights({
      locality,
      pin,
      geospatial,
      landmark,
      historical,
    });

    return NextResponse.json({
      status: "SUCCESS",
      message: "Scoring weights updated successfully in postal configuration engine.",
      weights: SCORING_WEIGHTS,
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || "Failed to update weights" }, { status: 500 });
  }
}

export async function POST(req: NextRequest) {
  return PUT(req);
}
