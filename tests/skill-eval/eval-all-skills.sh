#!/bin/bash
# eval-all-skills.sh - Run all skill trigger eval cases
# Reads skill-eval-cases.txt and tests each case
# Reports pass/fail counts and overall trigger rate

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
EVAL_SCRIPT="$SCRIPT_DIR/eval-skill-trigger.sh"
CASES_FILE="$SCRIPT_DIR/skill-eval-cases.txt"

if [ ! -f "$EVAL_SCRIPT" ]; then
    echo "ERROR: eval-skill-trigger.sh not found"
    exit 1
fi

if [ ! -f "$CASES_FILE" ]; then
    echo "ERROR: skill-eval-cases.txt not found"
    exit 1
fi

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0
FAILED_LIST=""

echo "============================================"
echo "  Skill Trigger Eval Report"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
echo ""

CURRENT_SECTION=""

while IFS= read -r line; do
    # Skip empty lines
    [[ -z "$line" ]] && continue
    # Print section headers
    if [[ "$line" =~ ^#.*===.*===$ ]]; then
        CURRENT_SECTION=$(echo "$line" | sed 's/^# *=* *//' | sed 's/ *=*$//')
        echo "--- $CURRENT_SECTION ---"
        continue
    fi
    # Skip comment lines
    [[ "$line" =~ ^# ]] && continue

    # Parse: skill_name | test_prompt | expected_keywords
    SKILL_NAME=$(echo "$line" | cut -d'|' -f1 | xargs)
    TEST_PROMPT=$(echo "$line" | cut -d'|' -f2 | xargs)
    EXPECTED_KW=$(echo "$line" | cut -d'|' -f3 | xargs)

    if [ -z "$SKILL_NAME" ] || [ -z "$TEST_PROMPT" ]; then
        continue
    fi

    TOTAL=$((TOTAL + 1))

    RESULT=$("$EVAL_SCRIPT" "$SKILL_NAME" "$TEST_PROMPT" "$EXPECTED_KW" 2>&1)
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        PASSED=$((PASSED + 1))
        echo "  $RESULT"
    elif [ $EXIT_CODE -eq 2 ]; then
        SKIPPED=$((SKIPPED + 1))
        echo "  $RESULT"
    else
        FAILED=$((FAILED + 1))
        echo "  $RESULT"
        FAILED_LIST="${FAILED_LIST}\n  - ${SKILL_NAME}: ${TEST_PROMPT}"
    fi
done < "$CASES_FILE"

RATE=0
if [ $TOTAL -gt 0 ]; then
    RATE=$(( (PASSED * 100) / (TOTAL - SKIPPED) ))
fi

echo ""
echo "============================================"
echo "  RESULTS"
echo "============================================"
echo "  Total:   $TOTAL"
echo "  Passed:  $PASSED"
echo "  Failed:  $FAILED"
echo "  Skipped: $SKIPPED"
echo "  Rate:    ${RATE}%"
echo ""

if [ $FAILED -gt 0 ]; then
    echo "  Failed cases:"
    echo -e "$FAILED_LIST"
    echo ""
fi

if [ $RATE -ge 80 ]; then
    echo "  STATUS: GREEN (≥80%)"
    exit 0
else
    echo "  STATUS: RED (<80%)"
    exit 1
fi
