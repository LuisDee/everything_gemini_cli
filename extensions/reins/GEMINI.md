# Workflow Extension

This extension provides three specialised subagents for structured development:

## Available Agents

- **investigator** — Deep investigation and root cause analysis. Read-only. Uses Docker MCP for container logs/state. Use when debugging errors, tracing bugs, or understanding how code works.
- **planner** — Creates TDD implementation plans with spec and plan files. Read-only (writes only to .gemini/plans/). Use after investigation or for new features.
- **reviewer** — Reviews implementation against spec and plan. Validates via browser automation (Playwright) and container inspection (Docker MCP). Read-only except for browser/container interaction.

## Workflow

1. **Investigate**: Delegate to the investigator agent with the problem description and logs
2. **Plan**: Delegate to the planner agent with what to fix/build, referencing the investigation
3. **Implement**: You (the main agent) execute the plan with human approval
4. **Review**: Delegate to the reviewer agent with what to review

> **Note**: Before delegating to any subagent, follow the **Orchestration Protocol** below to set up the plan directory and `current` symlink. After each subagent returns, persist its output per the protocol.

## Plans Directory

```
.gemini/plans/
  current -> 3        # symlink to active plan
  1/
    investigation.md
    spec.md
    plan.md
    review.md
  2/ ...
  3/ ...
```

- Plans numbered sequentially: `1/`, `2/`, `3/`...
- `.gemini/plans/current` symlink always points to the active plan directory
- All agents use `.gemini/plans/current/` — never a hardcoded number
- Files per plan:
  - `investigation.md` — output of the investigator
  - `spec.md` — acceptance criteria from the planner
  - `plan.md` — implementation tasks from the planner
  - `review.md` — output of the reviewer

## Orchestration Protocol (main agent responsibilities)

The main agent manages plan directories and persists subagent outputs.

### Starting a new plan
1. Determine next number: `ls .gemini/plans/ 2>/dev/null | grep -E '^[0-9]+$' | sort -n | tail -1` + 1 (default to 1)
2. Create directory: `mkdir -p .gemini/plans/<next>/`
3. Update symlink: `ln -sfn <next> .gemini/plans/current`

### After investigator returns
- Save `complete_task` result to `.gemini/plans/current/investigation.md`

### After planner returns
- No action needed (planner writes spec.md and plan.md directly to `.gemini/plans/current/`)

### After reviewer returns
- Save `complete_task` result to `.gemini/plans/current/review.md`

### Resuming an existing plan
- If `.gemini/plans/current` already points to the correct plan, no setup needed

## Tool Rules for Implementation Phase

When the main agent is implementing (not delegating to a subagent):

### File Editing — Hashline Only
- ALWAYS use `hashline__read_file` before editing (returns `42:a3|code` anchors)
- ALWAYS use `edit_file` with exact anchors from the most recent read
- ALWAYS re-read after every edit to verify
- One location per edit call. N changes = N separate edit calls.
- If edit reports changing more lines than intended: HALT. `git checkout -- <file>`, re-read, start over.

### Code Navigation — Serena
- Use `find_symbol` to locate definitions
- Use `find_symbol` with `include_body=True` to read implementations
- Use `get_symbols_overview` for file structure
- Use `find_referencing_symbols` to find all callers/usages
- NEVER use serena for editing — all edits go through hashline

### Search
- Text/string search: `grep_search` or `grep`
- Hash-anchored search (for immediate edit): `grep`
- Symbol search: `find_symbol`
