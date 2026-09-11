import { NextRequest, NextResponse } from "next/server";
import {
  detectLanguage,
  extractEntities,
  normalizeAddress,
  rankCandidates,
} from "@/app/lib/postal-store";

export interface BatchItemRequest {
  id?: string;
  raw_address: string;
}

export async function POST(req: NextRequest) {
  const startTime = Date.now();
  try {
    const body = await req.json();
    const items: (string | BatchItemRequest)[] = body.items || body.addresses || [];

    if (!Array.isArray(items) || items.length === 0) {
      return NextResponse.json(
        { detail: "Array of address strings or objects under 'items' is required." },
        { status: 400 }
      );
    }

    // Limit maximum batch size per API call to 5,000 for safety, chunk if higher
    const maxItems = Math.min(items.length, 5000);
    const processedResults = [];

    let conflictsCount = 0;
    let highConfidenceCount = 0;
    let reroutedCount = 0;

    for (let i = 0; i < maxItems; i++) {
      const item = items[i];
      const rawText = typeof item === "string" ? item : item.raw_address || "";
      const itemId = typeof item === "object" && item.id ? item.id : `REC-${(i + 1).toString().padStart(5, "0")}`;

      if (!rawText.trim()) continue;

      const detectedLang = detectLanguage(rawText);
      const normalized = normalizeAddress(rawText);
      const entities = extractEntities(rawText, normalized);
      const { candidates, conflictFlags, confidenceScore } = rankCandidates(rawText, normalized);

      const topCandidate = candidates[0] || null;
      const hasConflict = conflictFlags.length > 0;
      const isRerouted = hasConflict && topCandidate && topCandidate.pin_code !== entities.pin;

      if (hasConflict) conflictsCount++;
      if (confidenceScore >= 80) highConfidenceCount++;
      if (isRerouted) reroutedCount++;

      processedResults.push({
        id: itemId,
        raw_address: rawText,
        normalized_address: normalized,
        detected_language: detectedLang,
        confidence_score: confidenceScore,
        conflict_flags: conflictFlags,
        extracted_entities: entities,
        top_candidate: topCandidate
          ? {
              id: topCandidate.id,
              office_name: topCandidate.office_name,
              pin_code: topCandidate.pin_code,
              district: topCandidate.district,
              state: topCandidate.state,
              score: topCandidate.score,
            }
          : null,
        routing: {
          hub_code: topCandidate ? "NSH-MAA" : "UNASSIGNED",
          delivery_beat: topCandidate ? "Beat #01" : "General Delivery",
          status: confidenceScore >= 80 ? "RESOLVED_AUTO" : "FLAGGED_REVIEW",
        },
      });
    }

    const elapsedMs = Date.now() - startTime;
    const throughputPerSec = Math.round((processedResults.length / (elapsedMs || 1)) * 1000);

    return NextResponse.json({
      status: "SUCCESS",
      batch_summary: {
        total_submitted: items.length,
        total_processed: processedResults.length,
        high_confidence_count: highConfidenceCount,
        conflicts_count: conflictsCount,
        rerouted_count: reroutedCount,
        elapsed_milliseconds: elapsedMs,
        throughput_records_per_sec: throughputPerSec,
      },
      results: processedResults,
    });
  } catch (err: any) {
    return NextResponse.json(
      { detail: err?.message || "Failed to batch process addresses" },
      { status: 500 }
    );
  }
}
