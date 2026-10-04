const FPL_BASE = "https://fantasy.premierleague.com/api";
const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "cache-control": "private, max-age=60" };

async function fetchFpl(path) {
  const response = await fetch(`${FPL_BASE}${path}`, {
    headers: { "accept": "application/json", "user-agent": "FPL-Vortex-Website/1.0" },
  });
  if (!response.ok) {
    const error = new Error(`FPL API ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function onRequestGet(context) {
  const requestUrl = new URL(context.request.url);
  const entry = requestUrl.searchParams.get("entry")?.trim();
  if (!entry || !/^\d{1,10}$/.test(entry)) {
    return new Response(JSON.stringify({ error: "A numeric FPL entry ID is required." }), { status: 400, headers: JSON_HEADERS });
  }

  try {
    const [summary, history] = await Promise.all([
      fetchFpl(`/entry/${entry}/`),
      fetchFpl(`/entry/${entry}/history/`),
    ]);
    const requestedGw = Number(requestUrl.searchParams.get("gw"));
    const currentGw = Number.isInteger(requestedGw) && requestedGw > 0 ? requestedGw : Number(summary.current_event || 1);
    const picks = await fetchFpl(`/entry/${entry}/event/${currentGw}/picks/`);

    return new Response(JSON.stringify({ entry: Number(entry), gw: currentGw, summary, history, picks }), {
      status: 200,
      headers: JSON_HEADERS,
    });
  } catch (error) {
    const status = Number(error?.status) || 502;
    return new Response(JSON.stringify({ error: status === 404 ? "FPL manager not found." : "Could not reach the official FPL API.", status }), {
      status,
      headers: JSON_HEADERS,
    });
  }
}
