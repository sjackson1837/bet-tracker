/**
 * Bet Tracker - picks API
 *
 * Replaces the old localhost pick server so "I bet on this" works from your
 * phone, not just the Mac that happens to be running Python.
 *
 * Storage is a single JSON blob in KV: { "<game_id>": true, ... }
 * Only game_ids you've actually selected are kept, so it stays small.
 *
 * Routes:
 *   GET  /picks        -> { picks: { gameId: true, ... } }
 *   POST /toggle-pick  -> body { game_id } -> { game_id, user_selected }
 *   GET  /health       -> { ok: true }
 *
 * Deploy:  cd workers && npx wrangler deploy
 */

const ALLOWED_ORIGINS = [
  "https://sjackson1837.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
];

const KV_KEY = "picks";

function corsHeaders(request) {
  const origin = request.headers.get("Origin") || "";
  const allowed = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-Picks-Token",
    "Access-Control-Max-Age": "86400",
  };
}

function json(request, body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...corsHeaders(request),
    },
  });
}

async function readPicks(env) {
  const raw = await env.PICKS.get(KV_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

/**
 * Optional shared secret. If you set a PICKS_TOKEN secret on the Worker, writes
 * must present it. Reads stay open so the site can render without a token.
 * Without it the endpoint is world-writable -- low stakes for a personal
 * tracker, but it means anyone who finds the URL could toggle your checkboxes.
 */
function authorized(request, env) {
  if (!env.PICKS_TOKEN) return true;
  return request.headers.get("X-Picks-Token") === env.PICKS_TOKEN;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    if (url.pathname === "/health") {
      return json(request, { ok: true });
    }

    if (url.pathname === "/picks" && request.method === "GET") {
      return json(request, { picks: await readPicks(env) });
    }

    if (url.pathname === "/toggle-pick" && request.method === "POST") {
      if (!authorized(request, env)) {
        return json(request, { error: "unauthorized" }, 401);
      }

      let body;
      try {
        body = await request.json();
      } catch {
        return json(request, { error: "invalid JSON body" }, 400);
      }

      const gameId = body && body.game_id;
      if (!gameId || typeof gameId !== "string") {
        return json(request, { error: "game_id is required" }, 400);
      }

      const picks = await readPicks(env);
      const nowSelected = !picks[gameId];

      if (nowSelected) {
        picks[gameId] = true;
      } else {
        delete picks[gameId];
      }

      await env.PICKS.put(KV_KEY, JSON.stringify(picks));
      return json(request, { game_id: gameId, user_selected: nowSelected });
    }

    return json(request, { error: "not found" }, 404);
  },
};
