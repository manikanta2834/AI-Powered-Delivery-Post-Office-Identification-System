import { NextRequest, NextResponse } from "next/server";
import {
  detectLanguage,
  extractEntities,
  normalizeAddress,
  rankCandidates,
} from "@/app/lib/postal-store";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const address: string = body.address || "";
    const languageHint: string | undefined = body.language_hint;

    if (!address.trim()) {
      return NextResponse.json({ detail: "Address text is required." }, { status: 400 });
    }

    const detectedLang = detectLanguage(address, languageHint);
    const normalized = normalizeAddress(address);
    const entities = extractEntities(address, normalized);
    const { candidates, conflictFlags, confidenceScore } = rankCandidates(address, normalized);

    return NextResponse.json({
      analysis_id: `analysis-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      raw_address: address,
      normalized_address: normalized,
      detected_language: detectedLang,
      conflict_flags: conflictFlags,
      confidence_score: confidenceScore,
      extracted_entities: entities,
      candidates,
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || "Failed to process address" }, { status: 500 });
  }
}
