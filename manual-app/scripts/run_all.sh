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
  echo "note: no Anthropic credential found - LLM steps will be skipped (no-cost run)."
  TAG=free
else
  TAG=claude
fi

for c in manuals techmanualqa tenders; do python -m manual_app fetch --corpus "$c"; done
python -m manual_app vendor
python -m manual_app.validate_gold || echo "validator reported issues (see above); continuing"

python -m manual_app run --corpus manuals      --parsers "$ALL" --out "results/$DATE-manuals-$TAG"
python -m manual_app run --corpus techmanualqa --parsers "${ALL%,router}" --out "results/$DATE-techmanualqa-$TAG"
python -m manual_app run --corpus tenders      --parsers "$ALL" --out "results/$DATE-tenders-$TAG"
echo "Reports: results/$DATE-*-$TAG/report.md"
