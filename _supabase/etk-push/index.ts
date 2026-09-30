// ShowComm: push alerts for new crew key requests and ETK chat messages.
// Called by database triggers on INSERT into public.key_requests and public.messages (with an x-etk-secret header).
// Sends a push to every device saved in public.push_subscriptions (TMs with Alerts on).
import webpush from "npm:web-push@3.6.7";
import { createClient } from "npm:@supabase/supabase-js@2";

// Works with both Supabase key systems: the classic service_role key or the newer secret keys
function serverKey(): string {
  const legacy = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (legacy) return legacy;
  try { const j = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}"); return j.default ?? Object.values(j)[0] ?? ""; } catch { return ""; }
}
const sb = createClient(Deno.env.get("SUPABASE_URL")!, serverKey());
webpush.setVapidDetails(
  Deno.env.get("VAPID_SUBJECT") ?? "mailto:showpoint@example.com",
  Deno.env.get("VAPID_PUBLIC_KEY")!,
  Deno.env.get("VAPID_PRIVATE_KEY")!,
);

// "CAMS (PL)" → "Key 1 → CAMS", CLEAR → "Key 3 → clear", latch noted
function describe(noteJson: string): string {
  let entries: any[] = [];
  try { entries = JSON.parse(noteJson || "[]"); } catch { return ""; }
  if (!Array.isArray(entries)) return "";
  return entries.map((en) => {
    const key = `Key ${Number(en.keyIndex) + 1}`;
    if (en.note === "CLEAR") return `${key} → clear`;
    const m = /^(.+) \((PL|IFB)\)$/.exec(en.note || "");
    return `${key} → ${m ? m[1] : en.note}${en.latch ? " (latch)" : ""}`;
  }).join(", ");
}

// Sends to every saved device, or only to devices whose login has one of `roles`
async function sendTo(payload: string, roles: string[] | null, skipUser?: string) {
  const { data: subs } = await sb.from("push_subscriptions").select("endpoint, subscription, user_id");
  let list = subs ?? [];
  if (roles) {
    const ids = [...new Set(list.map((s: any) => s.user_id).filter(Boolean))];
    const { data: profs } = ids.length ? await sb.from("profiles").select("id, role").in("id", ids) : { data: [] };
    const roleOf = new Map<string, string>((profs ?? []).map((p: any) => [p.id, p.role]));
    list = list.filter((s: any) => roles.includes(roleOf.get(s.user_id) ?? "") && s.user_id !== skipUser);
  }
  let sent = 0;
  await Promise.all(list.map(async (s: any) => {
    try {
      await webpush.sendNotification(s.subscription, payload, { TTL: 3600, urgency: "high" });
      sent++;
    } catch (e: any) {
      if (e?.statusCode === 404 || e?.statusCode === 410) {
        await sb.from("push_subscriptions").delete().eq("endpoint", s.endpoint);
      } else console.error("push failed:", e?.statusCode, e?.body ?? e?.message);
    }
  }));
  return sent;
}

Deno.serve(async (req) => {
  // Only the database trigger knows this password (set as the ETK_PUSH_SECRET secret)
  if (req.headers.get("x-etk-secret") !== Deno.env.get("ETK_PUSH_SECRET")) return new Response("forbidden", { status: 401 });
  try {
    const body = await req.json();
    const r = body?.record;
    if (body?.type !== "INSERT" || !r) return new Response("skipped");

    // Chat: a TM message goes to admins (Matt); Matt's message goes to the TMs
    if (body?.table === "messages") {
      const fromAdmin = r.sender_role === "admin";
      const payload = JSON.stringify({
        title: `ETK · ${fromAdmin ? (r.sender_name || "Matt") : "TM"}`,
        body: String(r.body ?? "").slice(0, 180),
        tag: "etk-chat",
        url: "/showcomm/etk/index.html?role=tm#messages",
      });
      const sent = await sendTo(payload, fromAdmin ? ["tm"] : ["admin"], r.sender_id);
      return new Response(`chat sent ${sent}`);
    }

    if (r.status !== "open") return new Response("skipped");

    const { data: claim } = await sb.from("device_claims").select("crew_name")
      .eq("production_id", r.production_id).eq("device_id", r.device_id)
      .in("status", ["pending", "confirmed"]).order("claimed_at", { ascending: false })
      .limit(1).maybeSingle();

    const payload = JSON.stringify({
      title: `${r.device_id} · ${claim?.crew_name ?? "Crew"}`,
      body: describe(r.note) || "New key request",
      tag: `etk-${r.id}`,
      url: "/showcomm/etk/index.html?role=tm",
    });

    const sent = await sendTo(payload, null);   // key requests: every device with alerts on
    return new Response(`sent ${sent}`);
  } catch (e: any) {
    console.error("etk-push error:", e?.message ?? e);
    return new Response("error", { status: 200 });   // never make the webhook retry-storm
  }
});
