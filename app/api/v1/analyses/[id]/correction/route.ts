import { NextRequest, NextResponse } from "next/server";
import { HUMAN_CORRECTIONS } from "@/app/lib/postal-store";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await req.json();

    const correction = {
      id: `corr-${Date.now()}`,
      analysis_id: id,
      corrected_post_office_id: body.corrected_post_office_id || "",
      notes: body.notes || "",
      created_at: new Date().toISOString(),
    };

    HUMAN_CORRECTIONS.push(correction);

    return NextResponse.json({
      status: "SUCCESS",
      message: "Human-in-the-loop postal correction recorded successfully.",
      correction,
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || "Failed to record correction" }, { status: 500 });
  }
}
