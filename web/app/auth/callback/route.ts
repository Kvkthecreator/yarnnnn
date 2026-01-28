import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url);
  const code = searchParams.get("code");
  const error_param = searchParams.get("error");
  const error_description = searchParams.get("error_description");
  const next = searchParams.get("next") ?? "/dashboard";

  // If OAuth provider returned an error
  if (error_param) {
    console.error("OAuth error:", error_param, error_description);
    return NextResponse.redirect(
      `${origin}/auth/login?error=${encodeURIComponent(error_param)}&message=${encodeURIComponent(error_description || "")}`
    );
  }

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      // Redirect to the intended destination
      return NextResponse.redirect(`${origin}${next}`);
    }

    // Log the actual error for debugging
    console.error("Session exchange error:", error.message);
    return NextResponse.redirect(
      `${origin}/auth/login?error=session_error&message=${encodeURIComponent(error.message)}`
    );
  }

  // No code provided
  return NextResponse.redirect(`${origin}/auth/login?error=no_code`);
}
