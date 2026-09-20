import { cache } from "react";
import { createServerComponentClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";

export async function createClient() {
  const cookieStore = await cookies();
  return createServerComponentClient({ cookies: () => cookieStore });
}

/**
 * The signed-in user for THIS request, fetched once. The authenticated layout
 * and the locale resolver (ADR-660 D2) both need it; `cache` makes the second
 * reader free. Display use only — `updateSession` in the middleware remains the
 * sole auth gate.
 */
export const getRequestUser = cache(async () => {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  return user;
});
