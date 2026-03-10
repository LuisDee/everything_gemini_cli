---
name: gepa-optimizer
description: "Use when optimizing skill descriptions for activation, evaluating skill routing accuracy, creating eval data for skills, checking GEPA optimization status, or viewing optimization results."
origin: ECC
tools: read_file, write_file, replace, run_shell_command, grep_search, glob
---

# GEPA Skill Description Optimizer

Optimize Gemini CLI skill descriptions using GEPA (Generative Evolution with Pareto Alignment) with real CLI evaluation.

## Architecture

```
~/.gemini/scripts/skill_optimizer/
  optimizer.py           # Core GEPA evaluator (real CLI invocations only)
  batch_runner.py        # Sequential processor for all skills
  orchestrator-state.json # Tracks status of all 27 skills
  eval_data/             # Train/val prompt datasets per skill
  results/               # GEPA output per skill
  gepa-status.json       # Live heartbeat during runs

~/.gemini/scripts/
  run-gepa.sh            # Single-skill launcher (background)
  run-gepa-batch.sh      # All-skills launcher (background)

~/.gemini/hooks/ecc/
  skill-activation-logger.js  # BeforeTool hook logging activate_skill calls
```

## How It Works

1. The evaluator writes a candidate description to a skill's `SKILL.md` YAML frontmatter
2. Invokes `gemini -y --prompt "<test prompt>" --output-format json`
3. Reads `/tmp/gemini-skill-activations.log` (written by the BeforeTool hook)
4. Scores: **1.0** (target skill activated), **0.3** (wrong skill activated), **0.0** (no activation)
5. For negative examples: **1.0** (correctly NOT activated), **0.0** (false positive)
6. GEPA reflects on scores and proposes improved descriptions
7. Original description is always restored after optimization

## Workflows

### 1. Optimize a Single Skill

```bash
# Launch in background with monitoring
~/.gemini/scripts/run-gepa.sh --skill <skill-name> --max-calls 30

# Monitor progress
cat ~/.gemini/scripts/skill_optimizer/gepa-status.json | python3 -m json.tool

# View logs
tail -f ~/.gemini/scripts/gepa-output.log

# Stop
kill $(cat ~/.gemini/scripts/gepa.pid) && rm ~/.gemini/scripts/gepa.pid
```

### 2. Optimize All Pending Skills

```bash
# Reset skills to pending first (if re-running)
python3 -c "
import json
with open('$HOME/.gemini/scripts/skill_optimizer/orchestrator-state.json') as f:
    s = json.load(f)
for skill in s['skills']:
    s['skills'][skill]['status'] = 'pending'
    s['skills'][skill]['attempts'] = 0
with open('$HOME/.gemini/scripts/skill_optimizer/orchestrator-state.json', 'w') as f:
    json.dump(s, f, indent=2)
"

# Launch batch runner
~/.gemini/scripts/run-gepa-batch.sh --max-calls 30

# Monitor
cat ~/.gemini/scripts/skill_optimizer/orchestrator-state.json | \
  python3 -c "import sys,json; s=json.load(sys.stdin); c=sum(1 for v in s['skills'].values() if v['status']=='completed'); print(f'{c}/27 completed')"
```

### 3. Check Optimization Results

```bash
# Summary of all skills
python3 -c "
import json, glob
for f in sorted(glob.glob('$HOME/.gemini/scripts/skill_optimizer/results/*.json')):
    with open(f) as fh:
        d = json.load(fh)
    name = d['skill_name']
    seed_score = d.get('seed_score', '?')
    best_score = d.get('best_score', '?')
    changed = 'IMPROVED' if d.get('best_description') != d.get('seed_description') else 'SAME'
    print(f'{name:35s} seed={seed_score} best={best_score} {changed}')
"

# Detailed result for one skill
cat ~/.gemini/scripts/skill_optimizer/results/<skill-name>.json | python3 -m json.tool
```

### 4. Apply an Improved Description

Only if GEPA found an improvement (result shows IMPROVED):

```bash
python3 -c "
import json, yaml
with open('$HOME/.gemini/scripts/skill_optimizer/results/<skill-name>.json') as f:
    result = json.load(f)
if result['best_description'] == result['seed_description']:
    print('No improvement found, nothing to apply')
else:
    skill_md = '$HOME/.gemini/skills/<skill-name>/SKILL.md'
    with open(skill_md) as f:
        content = f.read()
    parts = content.split('---', 2)
    fm = yaml.safe_load(parts[1])
    fm['description'] = result['best_description']
    new_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True, width=200)
    with open(skill_md, 'w') as f:
        f.write('---\n' + new_yaml + '---' + parts[2])
    print(f'Applied: {result[\"best_description\"][:100]}')
"
```

Or use the `--apply` flag when running the optimizer:

```bash
~/.gemini/scripts/run-gepa.sh --skill <skill-name> --max-calls 30 --apply
```

### 5. Create Eval Data for a New Skill

Create `~/.gemini/scripts/skill_optimizer/eval_data/<skill-name>.json`:

```json
{
  "skill_name": "<skill-name>",
  "train": [
    {"prompt": "Easy positive prompt that clearly matches", "expected_skill": "<skill-name>", "should_activate": true, "difficulty": "easy"},
    {"prompt": "Medium positive prompt with indirect match", "expected_skill": "<skill-name>", "should_activate": true, "difficulty": "medium"},
    {"prompt": "Hard positive prompt with no keywords", "expected_skill": "<skill-name>", "should_activate": true, "difficulty": "hard"},
    {"prompt": "Negative prompt for a different domain", "expected_skill": "<skill-name>", "should_activate": false, "difficulty": "easy"},
    {"prompt": "Tricky negative that seems related but isn't", "expected_skill": "<skill-name>", "should_activate": false, "difficulty": "medium"}
  ],
  "val": [
    {"prompt": "Val positive prompt", "expected_skill": "<skill-name>", "should_activate": true, "difficulty": "medium"},
    {"prompt": "Val hard positive", "expected_skill": "<skill-name>", "should_activate": true, "difficulty": "hard"},
    {"prompt": "Val negative prompt", "expected_skill": "<skill-name>", "should_activate": false, "difficulty": "easy"},
    {"prompt": "Val tricky negative", "expected_skill": "<skill-name>", "should_activate": false, "difficulty": "medium"}
  ]
}
```

**Guidelines for eval data:**
- 8-11 train examples, 4-5 val examples
- Mix of easy/medium/hard difficulty
- ~70% positive (should_activate=true), ~30% negative (should_activate=false)
- Easy positives: contain skill keywords explicitly
- Medium positives: describe the task but without exact keywords
- Hard positives: describe the intent without any skill-specific vocabulary
- Easy negatives: clearly unrelated domain
- Medium negatives: adjacent domain that could be confused

### 6. Test Hook Logger

Verify the activation detection hook is working:

```bash
# Clear log
> /tmp/gemini-skill-activations.log

# Run a known-good prompt
gemini -y --prompt "Write a Python function using TDD, write the failing test first" --output-format json > /dev/null 2>&1

# Check activations
cat /tmp/gemini-skill-activations.log
```

Expected output: JSON lines with `tool_name: "activate_skill"` and `skill_name: "<activated-skill>"`.

### 7. Manual Scoring Test

Test scoring logic without running full GEPA:

```bash
PYTHONPATH=~/.gemini/scripts python3 -c "
from skill_optimizer.optimizer import evaluator, _read_current_description
desc = _read_current_description('<skill-name>')
score, info = evaluator(desc, {
    'prompt': '<test prompt>',
    'expected_skill': '<skill-name>',
    'should_activate': True,
    'difficulty': 'easy'
})
print(f'Score: {score}')
print(f'Activated: {info.get(\"activated\", [])}')
print(f'Timed out: {info.get(\"timed_out\", False)}')
"
```

## Key Technical Details

- **GEMINI_API_KEY** must be set (scripts use `pass show api/gemini`)
- **Timeout**: 180s per CLI invocation (gemini has ~30s startup latency)
- **Non-determinism**: CLI activates skills ~50-70% of the time; scores are inherently noisy
- **GEPA model**: Uses `gemini/gemini-3-flash-preview` via litellm for reflection
- **Hook**: `skill-activation-logger.js` runs as BeforeTool hook on `activate_skill` matcher
- **Safety**: Original SKILL.md description is always restored after optimization (even on crash via `finally` block)
- **Process management**: PID files prevent duplicate runs; `pkill -f "gemini.*--prompt"` kills stuck processes

## Interpreting Results

| Val Score | Meaning |
|-----------|---------|
| 0.5 | Typical baseline (negatives pass, positives are non-deterministic) |
| 0.6-0.7 | Good — positives activating more often than not |
| 0.8+ | Excellent — very reliable activation |
| < 0.5 | Description may be routing to wrong skills |

If GEPA returns SAME (seed = best), the current description is already near-optimal for the CLI's `utility_router`.
