#!/usr/bin/env bash
# Launch GEPA batch runner for ALL pending skills.
#
# Usage:
#   ./run-gepa-batch.sh
#   ./run-gepa-batch.sh --max-calls 20
#
# Monitoring:
#   cat ~/.gemini/scripts/skill_optimizer/gepa-status.json | python3 -m json.tool
#   cat ~/.gemini/scripts/skill_optimizer/orchestrator-state.json | python3 -m json.tool
#   tail -f ~/.gemini/scripts/gepa-batch-output.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNNER="$SCRIPT_DIR/skill_optimizer/batch_runner.py"
LOG_FILE="$SCRIPT_DIR/gepa-batch-output.log"
PID_FILE="$SCRIPT_DIR/gepa-batch.pid"

# Check for existing run
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Error: Batch runner already running (PID $OLD_PID)"
        echo "  Log: tail -f $LOG_FILE"
        echo "  Kill: kill $OLD_PID && rm $PID_FILE"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# Set up environment
export GEMINI_API_KEY="$(pass show api/gemini)"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

echo "=== GEPA Batch Runner ==="
echo "  Log:    $LOG_FILE"
echo "  State:  $SCRIPT_DIR/skill_optimizer/orchestrator-state.json"
echo "  Status: $SCRIPT_DIR/skill_optimizer/gepa-status.json"
echo ""

# Launch in background
nohup python3 "$RUNNER" "$@" > "$LOG_FILE" 2>&1 &

BATCH_PID=$!
echo "$BATCH_PID" > "$PID_FILE"

echo "Started batch runner (PID $BATCH_PID)"
echo ""
echo "Monitor with:"
echo "  tail -f $LOG_FILE"
echo "  cat $SCRIPT_DIR/skill_optimizer/orchestrator-state.json | python3 -c \"import sys,json; s=json.load(sys.stdin); print({k:v['status'] for k,v in s['skills'].items()})\""
echo "  kill $BATCH_PID && rm $PID_FILE  # stop"
