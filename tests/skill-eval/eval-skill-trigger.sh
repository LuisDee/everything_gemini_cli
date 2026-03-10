#!/bin/bash
# eval-skill-trigger.sh - Test if a skill description would trigger for a given prompt
# Usage: ./eval-skill-trigger.sh <skill_name> <test_prompt> [expected_keywords]
#
# Checks:
# 1. Action-oriented phrasing ("Use when", "Use this", etc.)
# 2. Keyword overlap between prompt and description
# 3. Description length (>15 words = better activation signal)
# Returns: PASS (score ≥3) or FAIL (score <3) with score out of 6

SKILL_DIR="$HOME/.gemini/skills"
SKILL_NAME="$1"
TEST_PROMPT="$2"
EXPECTED_KEYWORDS="$3"

if [ -z "$SKILL_NAME" ] || [ -z "$TEST_PROMPT" ]; then
    echo "Usage: $0 <skill_name> <test_prompt> [expected_keywords]"
    exit 1
fi

SKILL_FILE="$SKILL_DIR/$SKILL_NAME/SKILL.md"
if [ ! -f "$SKILL_FILE" ]; then
    echo "SKIP: $SKILL_NAME (SKILL.md not found)"
    exit 2
fi

# Extract description from YAML frontmatter
DESCRIPTION=$(awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description: */, ""); gsub(/"/, ""); print; exit}' "$SKILL_FILE")

if [ -z "$DESCRIPTION" ]; then
    echo "FAIL (0/6): $SKILL_NAME — no description found"
    exit 1
fi

SCORE=0
REASONS=""

# Check 1: Action-oriented phrasing (2 points)
if echo "$DESCRIPTION" | grep -qiE '(Use (when|this|for)|Activate when|Invoke when|Apply when|Run when)'; then
    SCORE=$((SCORE + 2))
    REASONS="${REASONS}+action "
else
    REASONS="${REASONS}-action "
fi

# Check 2: Keyword overlap (up to 3 points)
# Convert both to lowercase, extract significant words (>3 chars), count overlap
PROMPT_LOWER=$(echo "$TEST_PROMPT" | tr '[:upper:]' '[:lower:]')
DESC_LOWER=$(echo "$DESCRIPTION" | tr '[:upper:]' '[:lower:]')

OVERLAP=0
for word in $PROMPT_LOWER; do
    # Skip short words
    if [ ${#word} -le 3 ]; then continue; fi
    if echo "$DESC_LOWER" | grep -qi "$word"; then
        OVERLAP=$((OVERLAP + 1))
    fi
done

if [ $OVERLAP -ge 3 ]; then
    SCORE=$((SCORE + 3))
    REASONS="${REASONS}+kw($OVERLAP) "
elif [ $OVERLAP -ge 2 ]; then
    SCORE=$((SCORE + 2))
    REASONS="${REASONS}+kw($OVERLAP) "
elif [ $OVERLAP -ge 1 ]; then
    SCORE=$((SCORE + 1))
    REASONS="${REASONS}+kw($OVERLAP) "
else
    REASONS="${REASONS}-kw(0) "
fi

# Check 3: Description length (1 point if >15 words)
WORD_COUNT=$(echo "$DESCRIPTION" | wc -w | tr -d ' ')
if [ "$WORD_COUNT" -gt 15 ]; then
    SCORE=$((SCORE + 1))
    REASONS="${REASONS}+len($WORD_COUNT) "
else
    REASONS="${REASONS}-len($WORD_COUNT) "
fi

# Result
if [ $SCORE -ge 3 ]; then
    echo "PASS ($SCORE/6): $SKILL_NAME | $REASONS"
    exit 0
else
    echo "FAIL ($SCORE/6): $SKILL_NAME | $REASONS"
    exit 1
fi
