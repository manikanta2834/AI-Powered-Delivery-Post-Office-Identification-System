import { NextRequest, NextResponse } from "next/server";
import { USERS } from "@/app/lib/postal-store";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const email = (body.email || "").trim().toLowerCase();
    const totpCode = (body.totp_code || "").trim();

    if (!email) {
      return NextResponse.json({ detail: "Email is required." }, { status: 400 });
    }

    const user = USERS.get(email);
    if (!user) {
      return NextResponse.json({ detail: "User account not found." }, { status: 404 });
    }

    // Accepts 6-digit standard TOTP code (or demo code 123456)
    if (!totpCode || totpCode.length !== 6 || !/^\d{6}$/.test(totpCode)) {
      return NextResponse.json({ detail: "Invalid TOTP code. Enter 6 numeric digits." }, { status: 400 });
    }

    const accessToken = `jwt-token-${user.role}-${Date.now()}`;
    return NextResponse.json({
      access_token: accessToken,
      token_type: "bearer",
      expires_in_seconds: 3600,
      user: {
        id: user.id,
        email: user.email,
        full_name: user.full_name,
        role: user.role,
        is_active: user.is_active,
        created_at: user.created_at,
      },
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || "MFA verification failed" }, { status: 500 });
  }
}
