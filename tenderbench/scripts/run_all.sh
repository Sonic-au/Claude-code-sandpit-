#!/usr/bin/env bash
# Fetch corpora, build independent gold, parse with all seven local parsers and score every corpus.
# LLM steps (Claude) run when ANTHROPIC_API_KEY (or another Anthropic credential) is set; check the
# usage/cost line in each report. Estimated cost with all seven parsers at Claude Opus 5.5 prices: ~US$45.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f scripts/env.sh ] && . scripts/env.sh
DATE=$(date +%Y-%m-%d)
ALL=pypdf-text,pymupdf4llm,liteparse,liteparse-md,docling,mineru,router

if [ -z "${ANTHROPIC_API_KEY:-}${ANTHROPIC_AUTH_TOKEN:-}${TB_LLM_PROVIDER:-}" ]; then
  echo "note: no Anthropic credential found - LLM steps will be skipped (set ANTHROPIC_API_KEY to run them)."
fi

for c in manuals techmanualqa tenders; do python -m tenderbench fetch --corpus "$c"; done
python -m tenderbench vendor
python -m tenderbench.validate_gold || echo "validator reported issues (see above); continuing"

python -m tenderbench run --corpus manuals      --parsers "$ALL" --out "results/$DATE-manuals-claude"
python -m tenderbench run --corpus techmanualqa --parsers "${ALL%,router}" --out "results/$DATE-techmanualqa-claude"
python -m tenderbench run --corpus tenders      --parsers "$ALL" --out "results/$DATE-tenders-claude"
echo "Reports: results/$DATE-*-claude/report.md"
