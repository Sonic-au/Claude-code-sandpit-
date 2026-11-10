#!/bin/bash
# Start the Domain Finder server inside GitHub Codespaces.
# ANTHROPIC_API_KEY is injected from Codespaces secrets via devcontainer.json remoteEnv.

set -e

WORKDIR="/workspaces/claude-code-sandpit-/domain-finder"
LOG="/tmp/domain-finder.log"

echo "▶ Starting Domain Finder..."

if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo ""
  echo "⚠️  ANTHROPIC_API_KEY is not set."
  echo "   Add it as a Codespaces secret at:"
  echo "   https://github.com/settings/codespaces"
  echo "   Then rebuild the codespace."
  echo ""
fi

cd "$WORKDIR"
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload > "$LOG" 2>&1 &

echo "✓ Server running on port 8000 (logs: $LOG)"
