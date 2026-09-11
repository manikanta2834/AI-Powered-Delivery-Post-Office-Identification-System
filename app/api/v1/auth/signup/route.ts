import { NextRequest, NextResponse } from "next/server";
import { USERS, UserRecord } from "@/app/lib/postal-store";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const email = (body.email || "").trim().toLowerCase();
    const fullName = (body.full_name || "").trim();
    const password = (body.password || "").trim();
    const role: "citizen" | "operator" | "admin" = body.role || "citizen";

    if (!email || !email.includes("@")) {
      return NextResponse.json({ detail: "A valid email address is required." }, { status: 400 });
    }
    if (!fullName) {
      return NextResponse.json({ detail: "Full name is required." }, { status: 400 });
    }
    if (!password || password.length < 6) {
      return NextResponse.json({ detail: "Password must be at least 6 characters long." }, { status: 400 });
    }

    if (USERS.has(email)) {
      return NextResponse.json({ detail: "Email is already registered. Please sign in." }, { status: 409 });
    }

    const newUser: UserRecord = {
      id: `usr-${Date.now()}`,
      email,
      full_name: fullName,
      role,
      password,
      is_active: true,
      created_at: new Date().toISOString(),
    };

    USERS.set(email, newUser);

    const accessToken = `jwt-token-${role}-${Date.now()}`;
    return NextResponse.json({
      access_token: accessToken,
      token_type: "bearer",
      expires_in_seconds: 3600,
      user: {
        id: newUser.id,
        email: newUser.email,
        full_name: newUser.full_name,
        role: newUser.role,
        is_active: newUser.is_active,
        created_at: newUser.created_at,
      },
    });
  } catch (err: any) {
    return NextResponse.json({ detail: err?.message || "Registration failed" }, { status: 500 });
  }
}
