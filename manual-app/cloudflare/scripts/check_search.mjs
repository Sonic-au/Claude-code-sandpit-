// Check that the Worker's search returns exactly what the browser app's in-memory search returned.
//   node scripts/check_search.mjs [base_url] [questions.jsonl]   (default http://127.0.0.1:8787, ../gold/questions.jsonl)
// The reference below is the search code from the browser app, unchanged, run over seed/data.json. Every test
// question is searched twice: in its own manual, and across the whole library.
import fs from "node:fs";

const base = process.argv[2] || "http://127.0.0.1:8787", qfile = process.argv[3] || "../gold/questions.jsonl";
const data = JSON.parse(fs.readFileSync("seed/data.json", "utf8"));
const S = { data }, K = 8;
const manual = (id) => S.data.manuals.find((m) => m.id === id);
// ---- from web/app/index.html (browser app), verbatim
const tok = (s) => (s.toLowerCase().match(/[a-z0-9]+(?:[.%][0-9]+)?/g) || []);
const indexes = new Map();
const index = (key) => {
  if (indexes.has(key)) return indexes.get(key);
  const ms = key === 'all' ? S.data.manuals : [manual(key)];
  const chunks = ms.flatMap((m) => m.chunks.map((c) => ({ ...c, doc: m.id })));
  const docs = chunks.map((c) => tok(`${manual(c.doc).title} | ${c.heading} | ${c.text}`));
  const df = new Map(); docs.forEach((d) => new Set(d).forEach((t) => df.set(t, (df.get(t) || 0) + 1)));
  const N = docs.length, avg = docs.reduce((a, d) => a + d.length, 0) / Math.max(1, N), idf = new Map();
  for (const [t, n] of df) idf.set(t, Math.max(0.05, Math.log((N - n + 0.5) / (n + 0.5))));
  const tfs = docs.map((d) => { const f = new Map(); d.forEach((t) => f.set(t, (f.get(t) || 0) + 1)); return f; });
  const ix = { chunks, docs, tfs, idf, avg }; indexes.set(key, ix); return ix;
};
const search = (key, q) => { const ix = index(key), qt = [...new Set(tok(q))], k1 = 1.5, b = 0.75;
  return ix.tfs.map((f, i) => [qt.reduce((s, t) => { const tf = f.get(t) || 0; return tf ? s + (ix.idf.get(t) || 0) * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * ix.docs[i].length / ix.avg)) : s; }, 0), i])
    .filter(([s]) => s > 0).sort((a, b2) => b2[0] - a[0]).slice(0, K).map(([, i]) => ix.chunks[i]); };
// ---- end of browser code

const qs = fs.readFileSync(qfile, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l)).filter((x) => manual(x.doc));
const key = (xs) => xs.map((x) => `${x.doc}|${x.page}|${x.text}`).join("\n");
let same = 0, diff = 0; const t0 = Date.now(), times = [];
for (const x of qs) for (const doc of [x.doc, "all"]) {
  const t = Date.now();
  const r = await fetch(`${base}/api/search`, { method: "POST", body: JSON.stringify({ q: x.question, doc }) });
  const got = (await r.json()).extracts; times.push(Date.now() - t);
  if (key(got) === key(search(doc, x.question))) same++; else { diff++; if (diff <= 5) console.log("DIFF", x.id, doc); }
}
times.sort((a, b) => a - b);
console.log(`${qs.length} questions x 2 scopes: ${same} identical, ${diff} different; median ${times[times.length >> 1]} ms, slowest ${times.at(-1)} ms (local), total ${((Date.now() - t0) / 1000).toFixed(1)} s`);
process.exit(diff ? 1 : 0);
