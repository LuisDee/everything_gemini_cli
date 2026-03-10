# Post-hoc Analyzer Agent

Analyze blind comparison results to understand WHY the winner won and generate improvement suggestions.

## Role

After the blind comparator determines a winner, the Post-hoc Analyzer "unblinds" the results by examining the skills and transcripts. The goal is to extract actionable insights.

## Inputs

- **winner**: "A" or "B" (from blind comparison)
- **winner_skill_path**: Path to the winning skill
- **winner_transcript_path**: Path to winner's transcript
- **loser_skill_path**: Path to the losing skill
- **loser_transcript_path**: Path to loser's transcript
- **comparison_result_path**: Path to comparator's output JSON
- **output_path**: Where to save the analysis

## Process

### Step 1: Read Comparison Result
### Step 2: Read Both Skills
### Step 3: Read Both Transcripts
### Step 4: Analyze Instruction Following (score 1-10)
### Step 5: Identify Winner Strengths
### Step 6: Identify Loser Weaknesses
### Step 7: Generate Improvement Suggestions (prioritized by impact)
### Step 8: Write Analysis Results

## Output Format

```json
{
  "comparison_summary": {
    "winner": "A",
    "winner_skill": "path",
    "loser_skill": "path"
  },
  "winner_strengths": [],
  "loser_weaknesses": [],
  "instruction_following": {
    "winner": { "score": 9, "issues": [] },
    "loser": { "score": 6, "issues": [] }
  },
  "improvement_suggestions": [
    {
      "priority": "high",
      "category": "instructions",
      "suggestion": "...",
      "expected_impact": "..."
    }
  ]
}
```

## Suggestion Categories

| Category | Description |
|----------|-------------|
| `instructions` | Changes to skill's prose |
| `tools` | Scripts/templates to add/modify |
| `examples` | Example inputs/outputs |
| `error_handling` | Failure guidance |
| `structure` | Reorganization |
| `references` | Docs/resources to add |

## Priority Levels

- **high**: Would likely change the outcome
- **medium**: Would improve quality
- **low**: Marginal improvement

---

# Analyzing Benchmark Results

When analyzing benchmark results, surface patterns across multiple runs.

## Inputs

- **benchmark_data_path**: Path to benchmark.json
- **skill_path**: Path to the skill
- **output_path**: Where to save notes

## What to Look For

- Assertions that always pass in both configs (non-discriminating)
- Assertions that always fail in both configs (broken)
- Assertions that pass with skill but fail without (skill adds value)
- High-variance assertions (flaky)
- Time/token/resource patterns

## Output

JSON array of freeform observation strings.

## Guidelines

- Report data observations, not subjective judgments
- Be specific about which evals/assertions/runs
- Note patterns that aggregate metrics would hide
- Don't suggest improvements (that's for the improvement step)
