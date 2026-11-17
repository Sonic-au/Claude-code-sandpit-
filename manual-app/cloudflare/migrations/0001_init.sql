-- Manual Handling on Cloudflare D1.
-- Search is the app's BM25 keyword search, stored so the Worker can score it exactly as the browser app did:
-- chunk_terms holds each passage's term counts, scope_df the document frequency of each term within one manual
-- (scope = manual id) or the whole library (scope = '*'), and scopes the passage count and total length per scope.

CREATE TABLE manuals (
  id TEXT PRIMARY KEY,
  ord INTEGER NOT NULL,            -- library order; also the tie-break order for search
  corpus TEXT NOT NULL,            -- manuals | techmanualqa | hvac | requested
  title TEXT NOT NULL,
  maker TEXT,
  equipment TEXT,
  trust TEXT,                      -- vendor | third-party (manuals added from the web)
  source TEXT,                     -- where the PDF came from
  pages TEXT NOT NULL,             -- JSON array of the page numbers loaded
  total_pages INTEGER,
  pdf TEXT,                        -- file key of the PDF when pages are drawn from it
  figs TEXT,                       -- JSON {page: [[x0,y0,x1,y1], ...]} for PDF manuals
  examples TEXT,                   -- JSON array of example questions
  parser TEXT,
  security TEXT,                   -- JSON result of the ingestion scan
  added_at TEXT
);

CREATE TABLE pages (
  manual_id TEXT NOT NULL,
  page INTEGER NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY (manual_id, page)
) WITHOUT ROWID;

CREATE TABLE chunks (
  id INTEGER PRIMARY KEY,          -- assigned in library order, then passage order
  manual_id TEXT NOT NULL,
  page INTEGER NOT NULL,
  heading TEXT,
  text TEXT NOT NULL,
  len INTEGER NOT NULL             -- token count of "title | heading | text"
);
CREATE INDEX chunks_manual ON chunks (manual_id, id);

CREATE TABLE chunk_terms (
  term TEXT NOT NULL,
  manual_id TEXT NOT NULL,
  chunk_id INTEGER NOT NULL,
  tf INTEGER NOT NULL,
  len INTEGER NOT NULL,
  PRIMARY KEY (term, manual_id, chunk_id)
) WITHOUT ROWID;

CREATE TABLE scope_df (
  scope TEXT NOT NULL,
  term TEXT NOT NULL,
  df INTEGER NOT NULL,
  PRIMARY KEY (scope, term)
) WITHOUT ROWID;

CREATE TABLE scopes (
  scope TEXT PRIMARY KEY,
  n INTEGER NOT NULL,
  total_len INTEGER NOT NULL
);

CREATE TABLE feedback (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  question TEXT NOT NULL,
  doc TEXT,
  answer TEXT,
  cited TEXT,                      -- JSON [{doc, page}]
  retrieved TEXT,                  -- JSON [{doc, page}]
  verdict TEXT NOT NULL            -- right | wrong
);

-- Answers cost money and the app has no sign-in, so each answer is logged (by a hashed client address) for rate limits.
CREATE TABLE ask_log (
  id INTEGER PRIMARY KEY,
  client TEXT NOT NULL,
  at INTEGER NOT NULL              -- unix seconds
);
CREATE INDEX ask_log_client_at ON ask_log (client, at);
CREATE INDEX ask_log_at ON ask_log (at);
