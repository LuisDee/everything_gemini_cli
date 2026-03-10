---
name: skill-forge
description: >
  Use when creating new Gemini CLI skills, evaluating skill quality with test prompts,
  improving skills based on feedback, optimizing skill descriptions for trigger accuracy,
  or benchmarking skill performance with variance analysis. Covers the full skill lifecycle:
  create, eval, improve, describe, and benchmark.
---

# Skill Forge

A unified skill for creating, evaluating, and optimizing Gemini CLI skills.

## Overview

The skill lifecycle has 5 modes. Figure out where the user is and help them progress:

1. **CREATE** — Interview, draft SKILL.md, generate trigger eval set, validate
2. **EVAL** — Run test prompts with and without the skill, grade outputs, launch viewer
3. **IMPROVE** — Rewrite the skill body based on failures and user feedback
4. **DESCRIBE** — Optimize the description field for trigger accuracy
5. **BENCHMARK** — Multi-run with variance analysis and pattern detection

The core loop: draft/edit skill -> run test prompts -> review outputs with user -> improve -> repeat.

## Communicating with the user

Pay attention to context cues about the user's technical level. Terms like "evaluation" and "benchmark" are fine for most users; "JSON" and "assertion" need some cues that the user knows what those are. Briefly explain terms if in doubt.

---

## 1. CREATE Mode

### Capture Intent

1. What should this skill enable Gemini to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases? (Suggest based on skill type — objective outputs benefit from test cases, subjective outputs often don't.)

If the conversation already contains a workflow the user wants to capture, extract answers from it first.

### Interview and Research

Ask about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until you've ironed this out.

### Write the SKILL.md

Fill in these components:

- **name**: Kebab-case skill identifier (max 64 chars)
- **description**: When to trigger, what it does. This is the primary triggering mechanism. Include both what the skill does AND specific contexts. Use "Use when..." phrasing. Make descriptions a bit "pushy" to combat under-triggering.
- **the rest of the skill**

### Skill Writing Guide

#### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, etc.)
```

#### Gemini CLI Frontmatter

Allowed fields: `name`, `description`, `origin`, `tools`. No other fields.

```yaml
---
name: my-skill
description: >
  Use when the user wants to do X. Handles Y and Z.
---
```

Description max 1024 chars. The description field is what Gemini reads to decide whether to activate the skill — it is the ONLY routing mechanism.

#### Progressive Disclosure

1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — In context when skill activates (<500 lines ideal)
3. **Bundled resources** — Read as needed (unlimited, scripts can execute without loading)

Keep SKILL.md under 500 lines. Reference files clearly from SKILL.md. For large reference files (>300 lines), include a table of contents.

#### Writing Patterns

Prefer imperative form. Explain the **why** behind instructions rather than heavy-handed MUSTs. Use theory of mind and make skills general rather than narrow to specific examples.

### Test Cases

After drafting the skill, create 2-3 realistic test prompts. Share them with the user for sign-off. Save to `evals/evals.json`:

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See `references/schemas.md` for the full schema.

### Validation

After writing the SKILL.md, validate it:

```bash
python3 -m scripts.validate_skill <path-to-skill>
```

This checks frontmatter fields, naming conventions, description length, and structure. Run this from the skill-forge directory.

---

## 2. EVAL Mode

This section is one continuous sequence.

Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Within the workspace, organize by iteration (`iteration-1/`, etc.) and each test case gets a directory (`eval-0/`, etc.).

### Step 1: Run all test cases

For each test case, run two Gemini CLI invocations — one with the skill, one without.

**With-skill run:**
```bash
gemini -y --prompt "<eval prompt>" --output-format json
```
Save outputs to `<workspace>/iteration-N/eval-ID/with_skill/outputs/`.

**Baseline run** (same prompt, skill disabled):

Use the baseline manager to temporarily disable the skill:
```python
from scripts.baseline_manager import skill_disabled
with skill_disabled("my-skill"):
    # Run gemini CLI here — skill won't be found
    pass
```

This renames SKILL.md to `.SKILL.md.forge-disabled` so Gemini CLI won't discover it. The context manager restores it automatically.

Save baseline outputs to `without_skill/outputs/`.

Write an `eval_metadata.json` for each eval:
```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

### Step 2: Draft assertions while runs are in progress

Draft quantitative assertions for each test case. Good assertions are objectively verifiable and have descriptive names that read clearly in the benchmark viewer.

Update `eval_metadata.json` and `evals/evals.json` with the assertions.

### Step 3: Capture timing data

After each run completes, save timing data to `timing.json` in the run directory:
```json
{
  "total_duration_seconds": 23.3,
  "executor_start": "2026-01-15T10:30:00Z",
  "executor_end": "2026-01-15T10:32:45Z"
}
```

### Step 4: Grade, aggregate, and launch the viewer

1. **Grade each run** — read `agents/grader.md` and evaluate each assertion. Save to `grading.json`. The expectations array must use `text`, `passed`, and `evidence` fields — the viewer depends on these exact names.

2. **Aggregate into benchmark:**
   ```bash
   python3 -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```
   This produces `benchmark.json` and `benchmark.md`.

3. **Analyst pass** — read the benchmark data and surface patterns. See `agents/analyzer.md` ("Analyzing Benchmark Results" section).

4. **Launch the viewer:**
   ```bash
   nohup python3 skill-forge-path/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```
   For iteration 2+, add `--previous-workspace <workspace>/iteration-<N-1>`.

   If no browser/display is available, use `--static <output_path>` for a standalone HTML file.

5. **Tell the user** the viewer is open. Explain the two tabs (Outputs and Benchmark).

### What the user sees in the viewer

**Outputs tab** — one test case at a time:
- Prompt, Output files (rendered inline), Previous Output (collapsed), Formal Grades (collapsed), Feedback textbox, Previous Feedback

**Benchmark tab** — stats summary: pass rates, timing, token usage per configuration

### Step 5: Read the feedback

When the user is done, read `feedback.json` from the workspace. Empty feedback = looked good. Focus improvements on cases with specific complaints.

Kill the viewer: `kill $VIEWER_PID 2>/dev/null`

---

## 3. IMPROVE Mode

### How to think about improvements

1. **Generalize from feedback.** Skills will be used across many prompts. Don't overfit to test examples. Rather than fiddly constraints, try different metaphors or working patterns.

2. **Keep the prompt lean.** Remove things not pulling their weight. Read transcripts — if the skill makes the model waste time on unproductive steps, trim those parts.

3. **Explain the why.** Models are smart. Explain reasoning instead of using heavy-handed ALWAYS/NEVER. Transmit understanding, not just rules.

4. **Look for repeated work.** If all test runs independently wrote similar helper scripts, bundle that script in `scripts/` and reference it from the skill.

### The iteration loop

1. Apply improvements to the skill
2. Rerun all test cases into `iteration-<N+1>/`, including baselines
3. Launch the viewer with `--previous-workspace` pointing at previous iteration
4. Wait for user review
5. Read feedback, improve again, repeat

Keep going until:
- The user says they're happy
- Feedback is all empty
- Not making meaningful progress

### Programmatic skill improvement

For automated improvement based on grading failures:

```python
from scripts.improve_skill import improve_skill

new_content = improve_skill(
    skill_name="my-skill",
    skill_content=current_skill_content,
    grading_results=grading_data,
    user_feedback=feedback_data,
    comparison_results=comparison_data,  # optional
    model="claude-sonnet",
)
```

---

## 4. DESCRIBE Mode

Optimize the description field for better trigger accuracy. Two tools are available:

- **GEPA optimizer** (recommended) — uses the `gepa.optimize_anything` engine with real CLI invocations, gradient scoring, and LLM-powered reflection. Battle-tested across 27 skills. Best for thorough optimization.
- **Built-in loop** (`run_loop.py`) — lighter-weight alternative using direct LLM calls to propose improvements. Good for quick iterations or when GEPA isn't installed.

### Step 1: Generate trigger eval queries

Create eval data with train/val split — aim for 12+ train examples and 5+ val examples. Mix should-trigger and should-not-trigger cases.

**GEPA format** (recommended — used by both tools):

```json
{
  "train": [
    {"prompt": "realistic user prompt", "expected_skill": "my-skill", "should_activate": true, "difficulty": "easy"},
    {"prompt": "near-miss prompt", "expected_skill": "my-skill", "should_activate": false, "difficulty": "medium"}
  ],
  "val": [
    {"prompt": "held-out test prompt", "expected_skill": "my-skill", "should_activate": true, "difficulty": "hard"}
  ],
  "skill_name": "my-skill"
}
```

Save to `~/.gemini/scripts/skill_optimizer/eval_data/<skill-name>.json`.

**Flat format** (also accepted by both tools):

```json
[
  {"query": "the user prompt", "should_trigger": true},
  {"query": "another prompt", "should_trigger": false}
]
```

**Query quality matters.** Queries must be realistic — concrete, specific, with details like file paths, personal context, column names. Mix different lengths, focus on edge cases.

For should-trigger: different phrasings, some formal/casual, cases without explicit skill name but clearly needing it, uncommon use cases, cases competing with other skills.

For should-not-trigger: near-misses sharing keywords but needing something different, adjacent domains, ambiguous phrasing. Don't use obviously irrelevant queries.

### Step 2: Review with user

Present using the eval review template:

1. Read `assets/eval_review.html`
2. Replace placeholders: `__EVAL_DATA_PLACEHOLDER__` -> JSON array, `__SKILL_NAME_PLACEHOLDER__` -> name, `__SKILL_DESCRIPTION_PLACEHOLDER__` -> description
3. Write to temp file and open: `open /tmp/eval_review_<skill-name>.html`
4. User edits, then clicks "Export Eval Set" -> downloads `eval_set.json`
5. Check `~/Downloads/` for the file

### Step 3a: Run GEPA optimizer (recommended)

GEPA lives at `~/.gemini/scripts/skill_optimizer/` and uses the `gepa.optimize_anything` engine for gradient-based description optimization with real Gemini CLI invocations.

```bash
env GEMINI_API_KEY=$(pass show api/gemini) \
  python3 ~/.gemini/scripts/skill_optimizer/optimizer.py \
  --skill <skill-name> \
  --data ~/.gemini/scripts/skill_optimizer/eval_data/<skill-name>.json \
  --max-calls 30 \
  --apply
```

How GEPA works:
- Writes each candidate description to the skill's SKILL.md
- Invokes real `gemini -y --prompt` for each eval prompt (180s timeout per call)
- Reads the hook log (`/tmp/gemini-skill-activations.log`) to detect which skill activated
- **Gradient scoring**: 1.0 = target skill activated, 0.3 = wrong skill activated, 0.0 = no activation. For negatives: 1.0 = correctly not activated, 0.0 = false positive
- LLM reflection proposes improved descriptions based on scores
- Train/val split prevents overfitting — val scores select the best candidate
- Original description is always restored in a `finally` block (crash-safe via `.gepa-backup`)
- `--apply` writes the best description to SKILL.md if it improved

Monitor progress: `cat ~/.gemini/scripts/skill_optimizer/gepa-status.json`

Results saved to: `~/.gemini/scripts/skill_optimizer/results/<skill-name>.json`

**Important context from real-world testing:** Gemini CLI skill activation is inherently non-deterministic (~50-70% activation rate even for excellent descriptions). GEPA accounts for this through gradient scoring — a 0.3 for wrong-skill-activated is better signal than a flat 0.0. If GEPA can't improve on the seed description, the hand-crafted version is likely already near-optimal.

### Step 3b: Run built-in loop (lightweight alternative)

If GEPA isn't installed or you want a quicker iteration:

```bash
python3 -m scripts.run_loop \
  --eval-set <path-to-eval.json> \
  --skill-path <path-to-skill> \
  --model claude-sonnet \
  --max-iterations 5 \
  --verbose
```

This uses skill-forge's own scripts:
- Splits eval set 60/40 train/test (stratified by should_trigger)
- Evaluates current description via `gemini -y --prompt` with hook log detection
- Calls LLM (via LiteLLM proxy) to propose improved descriptions based on failures
- Re-evaluates on train + test each iteration
- Opens HTML report in browser when done

### Step 4: Apply the result

- **GEPA**: Use `--apply` flag, or read `results/<skill-name>.json` and apply `best_description` manually
- **Built-in loop**: Take `best_description` from the JSON output and update the skill's SKILL.md

---

## 5. BENCHMARK Mode

For rigorous comparison with variance analysis.

### Running a benchmark

For each eval, run multiple times (3+ recommended) in both configurations. Use the baseline manager for without-skill runs. Organize:

```
benchmarks/<timestamp>/
  eval-1/
    with_skill/
      run-1/  (outputs/, grading.json, timing.json)
      run-2/
      run-3/
    without_skill/
      run-1/
      run-2/
      run-3/
  eval-2/
    ...
```

### Aggregation

```bash
python3 -m scripts.aggregate_benchmark benchmarks/<timestamp> \
  --skill-name <name>
```

Produces `benchmark.json` with mean +/- stddev for pass_rate, time, and tokens per configuration, plus delta.

### Analysis

Read `agents/analyzer.md` for pattern detection:
- Assertions that always pass in both configs (non-discriminating)
- Assertions that always fail in both configs (broken)
- Assertions that pass with skill but fail without (skill adds value)
- High-variance assertions (flaky)
- Time/token patterns

### Blind Comparison (optional)

For more rigorous comparison, use the blind comparison system. Read `agents/comparator.md` and `agents/analyzer.md`. Give two outputs to an independent agent without revealing which is which.

---

## Crash Recovery

If a previous run was interrupted, orphaned disabled skills may exist. On startup, run:

```python
from scripts.baseline_manager import recover_all
recover_all()  # Restores any .SKILL.md.forge-disabled files
```

The optimization loop (`run_loop.py`) backs up the original SKILL.md before modifying descriptions and restores it in a `finally` block.

GEPA has its own crash recovery — it creates `.SKILL.md.gepa-backup` files and restores them via `_ensure_restored()` on startup. If you see a `.gepa-backup` file, GEPA was interrupted mid-optimization.

---

## Reference Files

### Agents

- `agents/grader.md` — How to evaluate assertions against outputs
- `agents/comparator.md` — How to do blind A/B comparison
- `agents/analyzer.md` — How to analyze patterns and extract insights

### Scripts (skill-forge built-in)

- `scripts/run_trigger_eval.py` — Trigger accuracy eval via Gemini CLI
- `scripts/run_output_eval.py` — Output quality eval with A/B comparison
- `scripts/run_loop.py` — Built-in eval + improve optimization loop (lightweight alternative to GEPA)
- `scripts/improve_description.py` — LLM-powered description improvement
- `scripts/improve_skill.py` — LLM-powered skill body improvement
- `scripts/aggregate_benchmark.py` — Multi-run statistics
- `scripts/generate_report.py` — Description optimization HTML report
- `scripts/validate_skill.py` — Skill structure validation
- `scripts/package_skill.py` — ZIP packaging for distribution
- `scripts/baseline_manager.py` — Skill disable/enable for A/B testing
- `scripts/gemini_api.py` — Stdlib HTTP client for LLM calls
- `scripts/utils.py` — SKILL.md parsing, hook log I/O

### GEPA Optimizer (external, recommended for DESCRIBE mode)

- `~/.gemini/scripts/skill_optimizer/optimizer.py` — GEPA-powered description optimization using `gepa.optimize_anything`, real CLI invocations, hook-based activation detection, and gradient scoring
- `~/.gemini/scripts/skill_optimizer/eval_data/` — Eval datasets per skill (GEPA format with train/val split)
- `~/.gemini/scripts/skill_optimizer/results/` — Optimization results per skill
- `~/.gemini/scripts/skill_optimizer/gepa-status.json` — Live progress during optimization
- `~/.gemini/hooks/ecc/skill-activation-logger.js` — Hook that logs skill activations to `/tmp/gemini-skill-activations.log` (required by both GEPA and skill-forge's trigger eval)

### Other

- `eval-viewer/generate_review.py` — Interactive HTML eval viewer
- `eval-viewer/viewer.html` — Viewer HTML template
- `assets/eval_review.html` — Eval set editor template
- `references/schemas.md` — JSON schemas for all data structures

---

## Packaging

After the skill is ready, package for distribution:

```bash
python3 -m scripts.package_skill <path/to/skill-folder>
```

Creates a `.skill` file (ZIP format) excluding `__pycache__`, `node_modules`, `evals/`, etc.
