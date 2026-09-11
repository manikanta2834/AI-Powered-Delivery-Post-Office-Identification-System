import { NextRequest, NextResponse } from "next/server";
import { USERS } from "@/app/lib/postal-store";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const email = (body.email || "").trim().toLowerCase();
    const password = (body.password || "").trim();

    if (!email || !password) {
      return NextResponse.json({ detail: "Email and password are required." }, { status: 400 });
    }

    const user = USERS.get(email);
    if (!user || user.password !== password) {
      return NextResponse.json(
        { detail: "Invalid credentials. Please verify your email and password." },
        { status: 401 }
      );
    }

    // Operator and Admin require MFA
    if (user.role === "operator" || user.role === "admin") {
      return NextResponse.json({
        status: "MFA_REQUIRED",
        email: user.email,
        message: "Enter 6-digit TOTP code from your authenticator app (demo: 123456).",
      });
    }

    // Citizen login direct
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
    return NextResponse.json({ detail: err?.message || "Login failed" }, { status: 500 });
  }
}
