import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const jsonHeaders = {
  "Content-Type": "application/json",
};

Deno.serve(async (req) => {
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "method_not_allowed" }), {
      status: 405,
      headers: jsonHeaders,
    });
  }

  const refreshSecret = Deno.env.get("REFRESH_SECRET") ?? "";
  const auth = req.headers.get("Authorization") ?? "";
  if (!refreshSecret || auth !== `Bearer ${refreshSecret}`) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: jsonHeaders,
    });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  if (!supabaseUrl || !serviceRoleKey) {
    return new Response(JSON.stringify({ error: "missing_supabase_function_secrets" }), {
      status: 500,
      headers: jsonHeaders,
    });
  }

  const body = await req.json().catch(() => ({}));
  const requestedLimit = Math.min(Math.max(Number(body.limit ?? 10), 1), 100);
  const reason = String(body.reason ?? "manual").slice(0, 200);

  const supabase = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false },
  });

  const { data, error } = await supabase
    .from("pipeline_refresh_requests")
    .insert({
      reason,
      requested_limit: requestedLimit,
      status: "queued",
    })
    .select("id, reason, requested_limit, status, requested_at")
    .single();

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: jsonHeaders,
    });
  }

  return new Response(JSON.stringify({ queued: true, request: data }), {
    status: 202,
    headers: jsonHeaders,
  });
});
