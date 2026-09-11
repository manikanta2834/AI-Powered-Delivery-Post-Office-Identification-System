import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    status: "healthy",
    service: "India Post Postal Intelligence Engine",
    database: "online (PostGIS In-Memory Grounded)",
    version: "2026.1.0",
    timestamp: new Date().toISOString(),
  });
}
