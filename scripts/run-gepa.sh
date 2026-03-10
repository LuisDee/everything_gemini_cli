#!/usr/bin/env bash
# Launch GEPA skill optimizer in the background with monitoring.
#
# Usage:
#   ./run-gepa.sh --skill tdd-workflow
#   ./run-gepa.sh --skill tdd-workflow --max-calls 50
#   ./run-gepa.sh --skill tdd-workflow --apply
#
# Monitoring:
#   cat ~/.gemini/scripts/skill_optimizer/gepa-status.json | python3 -m json.tool
#   tail -f ~/.gemini/scripts/gepa-output.log

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPTIMIZER="$SCRIPT_DIR/skill_optimizer/optimizer.py"
LOG_FILE="$SCRIPT_DIR/gepa-output.log"
PID_FILE="$SCRIPT_DIR/gepa.pid"
STATUS_FILE="$SCRIPT_DIR/skill_optimizer/gepa-status.json"

# Extract --skill value, collect remaining args
SKILL=""
PASS_THROUGH=()
SKIP_NEXT=false
for arg in "$@"; do
    if $SKIP_NEXT; then
        SKILL="$arg"
        SKIP_NEXT=false
    elif [[ "$arg" == "--skill" ]]; then
        SKIP_NEXT=true
    else
        PASS_THROUGH+=("$arg")
    fi
done

if [[ -z "$SKILL" ]]; then
    echo "Error: --skill is required"
    echo "Usage: $0 --skill <skill-name> [--max-calls N] [--apply]"
    exit 1
fi

# Check for existing run
if [[ -f "$PID_FILE" ]]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Error: GEPA is already running (PID $OLD_PID)"
        echo "  Status: cat $STATUS_FILE | python3 -m json.tool"
        echo "  Log:    tail -f $LOG_FILE"
        echo "  Kill:   kill $OLD_PID && rm $PID_FILE"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# Set up environment
export GEMINI_API_KEY="$(pass show api/gemini)"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

# Resolve eval data path
DATA_FILE="$SCRIPT_DIR/skill_optimizer/eval_data/${SKILL}.json"
if [[ ! -f "$DATA_FILE" ]]; then
    echo "Error: eval data not found at $DATA_FILE"
    exit 1
fi

echo "=== GEPA Skill Optimizer ==="
echo "  Skill:  $SKILL"
echo "  Data:   $DATA_FILE"
echo "  Log:    $LOG_FILE"
echo "  Status: $STATUS_FILE"
echo "  PID:    $PID_FILE"
echo ""

# Launch in background (PYTHONUNBUFFERED for real-time log output)
export PYTHONUNBUFFERED=1
nohup python3 "$OPTIMIZER" \
    --skill "$SKILL" \
    --data "$DATA_FILE" \
    ${PASS_THROUGH[@]+"${PASS_THROUGH[@]}"} \
    > "$LOG_FILE" 2>&1 &

GEPA_PID=$!
echo "$GEPA_PID" > "$PID_FILE"

echo "Started GEPA (PID $GEPA_PID)"
echo ""
echo "Monitor with:"
echo "  cat $STATUS_FILE | python3 -m json.tool   # status heartbeat"
echo "  tail -f $LOG_FILE                          # full output"
echo "  kill $GEPA_PID && rm $PID_FILE             # stop"
