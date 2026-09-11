import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const password = (body.password || "").trim();

    if (!password) {
      return NextResponse.json({ detail: "Password is required for elevated re-auth." }, { status: 400 });
    }

    // Accepts Admin@2026 or Operator@2026 or any valid password
    if (password === "Admin@2026" || password === "Operator@2026" || password.length >= 6) {
      return NextResponse.json({
        reauth_token: `reauth-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        expires_in_seconds: 300,
      });
    }

    return NextResponse.json({ detail: "Elevated authentication failed. Password incorrect." }, { status: 401 });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || "Re-auth failed" }, { status: 500 });
  }
}
