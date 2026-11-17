// Manual Handling API on Cloudflare Workers. Static files (the app, page images, figures) are served by the
// assets binding before this code runs; everything else arrives here.
import Anthropic from "@anthropic-ai/sdk";
import { search } from "./search.js";
import { buildPrompt, SYSTEM } from "./prompt.js";

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8", "x-content-type-options": "nosniff" };
const json = (body, status = 200, extra = {}) => new Response(JSON.stringify(body), { status, headers: { ...JSON_HEADERS, ...extra } });
const bad = (msg, status = 400) => json({ error: msg }, status);
const parseJson = (s, d) => { try { return s ? JSON.parse(s) : d; } catch { return d; } };

async function titles(db) {
  const rows = (await db.prepare("SELECT id, title FROM manuals").all()).results;
  return new Map(rows.map((r) => [r.id, r.title]));
}

async function listManuals(env) {
  const rows = (await env.DB.prepare("SELECT id, corpus, title, maker, equipment, trust, source, pages, total_pages, pdf, figs, examples FROM manuals ORDER BY ord").all()).results;
  return json({ manuals: rows.map((r) => ({ ...r, pages: parseJson(r.pages, []), figs: parseJson(r.figs, null), examples: parseJson(r.examples, []) })) }, 200, { "cache-control": "public, max-age=60" });
}

async function pageTexts(env, url) {
  const doc = url.searchParams.get("doc") || "", ps = (url.searchParams.get("p") || "").split(",").map(Number).filter((n) => Number.isInteger(n) && n > 0).slice(0, 12);
  if (!doc || !ps.length) return bad("doc and p are required");
  const rows = (await env.DB.prepare(`SELECT page, text FROM pages WHERE manual_id = ? AND page IN (${ps.map(() => "?").join(",")})`).bind(doc, ...ps).all()).results;
  return json({ doc, pages: Object.fromEntries(rows.map((r) => [r.page, r.text])) }, 200, { "cache-control": "public, max-age=300" });
}

async function readQuestion(request, env) {
  const body = await request.json().catch(() => null);
  const q = typeof body?.q === "string" ? body.q.trim().slice(0, 1000) : "", doc = typeof body?.doc === "string" ? body.doc : "all";
  if (!q) return { error: bad("q is required") };
  const t = await titles(env.DB);
  if (doc !== "all" && !t.has(doc)) return { error: bad("unknown manual") };
  return { q, doc, titles: t, body };
}

async function clientKey(request) {
  const ip = request.headers.get("cf-connecting-ip") || "local";
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("mh:" + ip));
  return [...new Uint8Array(d)].slice(0, 12).map((b) => b.toString(16).padStart(2, "0")).join("");
}

// Answers cost money and the app is open to anyone, so limit them per client and per day.
async function overLimit(env, client) {
  const now = Math.floor(Date.now() / 1000), day = now - (now % 86400);
  const [mine, today] = await env.DB.batch([
    env.DB.prepare("SELECT count(*) AS n FROM ask_log WHERE client = ? AND at > ?").bind(client, now - 3600),
    env.DB.prepare("SELECT count(*) AS n FROM ask_log WHERE at >= ?").bind(day),
  ]);
  if (mine.results[0].n >= Number(env.MH_ASKS_PER_CLIENT_PER_HOUR || 30)) return "You've asked a lot of questions in the last hour. Try again in a little while.";
  if (today.results[0].n >= Number(env.MH_ASKS_PER_DAY || 500)) return "The app has reached today's limit for written answers. The matching passages are still shown below.";
  await env.DB.batch([
    env.DB.prepare("INSERT INTO ask_log (client, at) VALUES (?, ?)").bind(client, now),
    env.DB.prepare("DELETE FROM ask_log WHERE at < ?").bind(now - 3 * 86400),
  ]);
  return null;
}

async function doSearch(request, env) {
  const r = await readQuestion(request, env); if (r.error) return r.error;
  return json({ extracts: await search(env.DB, r.q, r.doc) });
}

// POST /api/ask -> newline-delimited JSON: {"extracts": [...]}, then {"t": "<text>"} pieces, then {"done": true, "stop": ...}
// or {"error": "<plain message>", "code": ...}. The passages always arrive, so the app can show them even when no answer does.
async function ask(request, env, ctx) {
  const r = await readQuestion(request, env); if (r.error) return r.error;
  const extracts = await search(env.DB, r.q, r.doc);
  const { readable, writable } = new TransformStream();
  const w = writable.getWriter(), enc = new TextEncoder(), send = (o) => w.write(enc.encode(JSON.stringify(o) + "\n"));
  const work = (async () => {
    try {
      await send({ extracts });
      if (!extracts.length) { await send({ done: true, stop: "nomatch" }); return; }
      const limited = await overLimit(env, await clientKey(request));
      if (limited) { await send({ error: limited, code: "rate_limited" }); return; }
      const prompt = buildPrompt(r.q, extracts, r.doc, r.titles);
      if (env.MH_FAKE_LLM === "1") {   // local testing only, set in .dev.vars
        for (const piece of ["From the extracts: ", "see the value on the cited page ", "[1]."]) { await send({ t: piece }); await new Promise((res) => setTimeout(res, 120)); }
        await send({ done: true, stop: "end_turn", fake: true }); return;
      }
      if (!env.ANTHROPIC_API_KEY) { await send({ error: "Written answers are not set up on this server yet. The matching passages are below.", code: "not_configured" }); return; }
      const client = new Anthropic({ apiKey: env.ANTHROPIC_API_KEY });
      const stream = client.beta.messages.stream({
        model: env.MH_MODEL || "claude-opus-5-5",
        max_tokens: 16000,
        output_config: { effort: env.MH_EFFORT || "medium" },
        betas: ["server-side-fallback-2026-07-01"],
        fallbacks: "default",   // if the model declines, the API retries on a suitable fallback model in the same call
        system: SYSTEM,
        messages: [{ role: "user", content: prompt }],
      });
      for await (const ev of stream) if (ev.type === "content_block_delta" && ev.delta.type === "text_delta") await send({ t: ev.delta.text });
      const final = await stream.finalMessage();
      await send({ done: true, stop: final.stop_reason, model: final.model });
    } catch (e) {
      const code = e instanceof Anthropic.RateLimitError ? "busy" : e instanceof Anthropic.AuthenticationError ? "not_configured" : e instanceof Anthropic.APIError ? "upstream" : "server";
      console.error("ask failed", code, e?.status, e?.message);
      await send({ error: code === "busy" ? "Claude is busy right now. Try again in a minute." : "The answer could not be written this time. The matching passages are below.", code }).catch(() => {});
    } finally { await w.close().catch(() => {}); }
  })();
  ctx.waitUntil(work);
  return new Response(readable, { headers: { "content-type": "application/x-ndjson; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff" } });
}

async function feedback(request, env) {
  const b = await request.json().catch(() => null);
  if (!b || typeof b.question !== "string" || !["right", "wrong"].includes(b.verdict)) return bad("question and verdict are required");
  const pairs = (xs) => JSON.stringify((Array.isArray(xs) ? xs : []).slice(0, 12).map((x) => ({ doc: String(x?.doc || "").slice(0, 80), page: Number(x?.page) || 0 })));
  await env.DB.prepare("INSERT INTO feedback (at, question, doc, answer, cited, retrieved, verdict) VALUES (?, ?, ?, ?, ?, ?, ?)")
    .bind(new Date().toISOString(), b.question.slice(0, 1000), String(b.doc || "").slice(0, 80), String(b.answer || "").slice(0, 8000), pairs(b.cited), pairs(b.retrieved), b.verdict).run();
  return json({ ok: true });
}

// Manual files added after deployment live in R2 under the same path; files shipped with the app are static assets.
async function file(request, env, url) {
  const key = decodeURIComponent(url.pathname.slice(1));
  if (!/^files\/[A-Za-z0-9_./-]+$/.test(key) || key.includes("..")) return env.ASSETS.fetch(request);
  const obj = env.FILES ? await env.FILES.get(key) : null;
  if (!obj) return env.ASSETS.fetch(request);
  const h = new Headers(); obj.writeHttpMetadata(h); h.set("etag", obj.httpEtag); h.set("cache-control", "public, max-age=86400"); h.set("x-content-type-options", "nosniff");
  return new Response(obj.body, { headers: h });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url), p = url.pathname, m = request.method;
    try {
      if (p === "/api/manuals" && m === "GET") return await listManuals(env);
      if (p === "/api/pages" && m === "GET") return await pageTexts(env, url);
      if (p === "/api/search" && m === "POST") return await doSearch(request, env);
      if (p === "/api/ask" && m === "POST") return await ask(request, env, ctx);
      if (p === "/api/feedback" && m === "POST") return await feedback(request, env);
      if (p === "/api/health") return json({ ok: true, manuals: (await env.DB.prepare("SELECT count(*) AS n FROM manuals").first()).n });
      if (p.startsWith("/api/")) return bad("not found", 404);
      if (p.startsWith("/files/") && m === "GET") return await file(request, env, url);
      return env.ASSETS.fetch(request);
    } catch (e) {
      console.error("request failed", p, e?.message);
      return bad("server error", 500);
    }
  },
};
