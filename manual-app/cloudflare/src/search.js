// The app's keyword search (BM25), scored exactly as the browser app scored it: same tokens, k1 = 1.5, b = 0.75,
// IDF floored at 0.05, IDF and average length taken over the manual searched (or the whole library), terms summed
// in question order, ties kept in library order. The database holds the counts; the arithmetic happens here.
export const K = 8;
const K1 = 1.5, B = 0.75, BATCH = 90;   // D1 allows 100 bound parameters per statement

export const tok = (s) => s.toLowerCase().match(/[a-z0-9]+(?:[.%][0-9]+)?/g) || [];

const inList = (n) => Array.from({ length: n }, () => "?").join(",");
const batches = (xs) => { const out = []; for (let i = 0; i < xs.length; i += BATCH) out.push(xs.slice(i, i + BATCH)); return out; };

export async function search(db, question, doc) {
  const qt = [...new Set(tok(question))];
  if (!qt.length) return [];
  const scope = doc === "all" ? "*" : doc;
  const sc = await db.prepare("SELECT n, total_len FROM scopes WHERE scope = ?").bind(scope).first();
  if (!sc) return [];
  const N = sc.n, avg = sc.total_len / Math.max(1, N);

  const stmts = [];
  for (const b of batches(qt)) {
    stmts.push(db.prepare(`SELECT term, df FROM scope_df WHERE scope = ? AND term IN (${inList(b.length)})`).bind(scope, ...b));
    stmts.push(scope === "*"
      ? db.prepare(`SELECT chunk_id, term, tf, len FROM chunk_terms WHERE term IN (${inList(b.length)})`).bind(...b)
      : db.prepare(`SELECT chunk_id, term, tf, len FROM chunk_terms WHERE term IN (${inList(b.length)}) AND manual_id = ?`).bind(...b, scope));
  }
  const res = await db.batch(stmts);
  const idf = new Map(), hits = new Map();
  res.forEach((r, i) => {
    if (i % 2 === 0) for (const { term, df } of r.results) idf.set(term, Math.max(0.05, Math.log((N - df + 0.5) / (df + 0.5))));
    else for (const { chunk_id, term, tf, len } of r.results) {
      let h = hits.get(chunk_id); if (!h) hits.set(chunk_id, (h = { len, tf: new Map() })); h.tf.set(term, tf);
    }
  });
  const scored = [];
  for (const [id, h] of hits) {
    const s = qt.reduce((s, t) => { const tf = h.tf.get(t) || 0; return tf ? s + (idf.get(t) || 0) * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * h.len / avg)) : s; }, 0);
    if (s > 0) scored.push([s, id]);
  }
  scored.sort((a, b) => b[0] - a[0] || a[1] - b[1]);
  const top = scored.slice(0, K).map(([, id]) => id);
  if (!top.length) return [];
  const rows = (await db.prepare(`SELECT id, manual_id, page, heading, text FROM chunks WHERE id IN (${inList(top.length)})`).bind(...top).all()).results;
  const byId = new Map(rows.map((r) => [r.id, r]));
  return top.map((id) => { const r = byId.get(id); return { doc: r.manual_id, page: r.page, heading: r.heading, text: r.text }; });
}
