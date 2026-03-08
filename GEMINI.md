<!-- BEGIN ECC RULES: workflows -->
# ECC Workflow Commands

| Workflow | Invoke | Description |
|---|---|---|
| TDD | `@ecc-tdd-guide` | Test-driven development, 80%+ coverage |
| Plan | `@ecc-planner` | Implementation plans before coding |
| Code Review | `@ecc-code-reviewer` | Comprehensive code quality review |
| Build Fix | `@ecc-build-error-resolver` | Fix build/type errors incrementally |
| Security | `@ecc-security-reviewer` | Security vulnerability detection |
| E2E | `@ecc-e2e-runner` | End-to-end testing |
| Refactor | `@ecc-refactor-cleaner` | Dead code cleanup and consolidation |
| Architecture | `@ecc-architect` | System design and technical decisions |
| Go Review | `@ecc-go-reviewer` | Idiomatic Go code review |
| Go Build | `@ecc-go-build-resolver` | Fix Go build/vet errors |
| Python Review | `@ecc-python-reviewer` | PEP 8, type hints, Pythonic idioms |
| Database | `@ecc-database-reviewer` | PostgreSQL query optimization and schema |
| Docs | `@ecc-doc-updater` | Update documentation and codemaps |
| Harness | `@ecc-harness-optimizer` | Optimize agent harness configuration |
| Loop | `@ecc-loop-operator` | Operate autonomous agent loops |
| Chief of Staff | `@ecc-chief-of-staff` | Triage multi-channel communications |
<!-- END ECC RULES: workflows -->

<!-- BEGIN ECC RULES: quality -->
# Code Quality Standards (ECC)

- Functions: max 50 lines
- Files: max 800 lines
- No console.log in production
- Immutable patterns preferred
- KISS, DRY, YAGNI
- Explicit error handling
- Conventional commits (feat/fix/chore/docs/refactor)
- Do NOT add Co-Authored-By trailers
<!-- END ECC RULES: quality -->

<!-- BEGIN ECC RULES: security -->
# Security Standards (ECC)

- Never hardcode API keys or secrets
- Validate all user input at system boundaries
- Use parameterized queries, never string interpolation for SQL
- Secrets via `pass` (GPG-encrypted at ~/.password-store/)
- OWASP Top 10 awareness: XSS, CSRF, injection, auth bypass
- Use HTTPS everywhere, verify TLS certificates
<!-- END ECC RULES: security -->

<!-- BEGIN ECC RULES: skills -->
# Available Skills (ECC)

| Skill | Description |
|---|---|
| tdd-workflow | Test-driven development with 80%+ coverage |
| security-review | Security vulnerability detection |
| backend-patterns | Backend architecture and API design |
| coding-standards | Universal coding standards (TS/JS/React/Node) |
| strategic-compact | Context compaction at logical intervals |
| frontend-patterns | React, Next.js, state management |
| api-design | REST API design patterns |
| iterative-retrieval | Progressive context retrieval |
| python-patterns | Pythonic idioms and PEP 8 |
| python-testing | pytest, TDD, fixtures, mocking |
| cost-aware-llm-pipeline | LLM cost optimization patterns |
| e2e-testing | Playwright E2E testing |
| eval-harness | Eval-driven development framework |
| database-migrations | Schema changes and zero-downtime deploys |
| postgres-patterns | PostgreSQL query and schema optimization |
| deployment-patterns | CI/CD, Docker, health checks |
| docker-patterns | Container security and networking |
| regex-vs-llm-structured-text | Regex vs LLM decision framework |
| content-hash-cache-pattern | SHA-256 content hash caching |
| verification-loop | Comprehensive verification system |
| search-first | Research-before-coding workflow |
| agentic-engineering | Eval-first execution and decomposition |
| plankton-code-quality | Write-time code quality enforcement |
| ai-first-engineering | AI agent engineering operating model |
| continuous-agent-loop | Autonomous agent loops with quality gates |
| continuous-learning | Extract patterns from sessions |
<!-- END ECC RULES: skills -->

<!-- BEGIN ECC RULES: hooks -->
# Hook Profile System

Set `ECC_HOOK_PROFILE` env var: `minimal` | `standard` (default) | `strict`

- **minimal**: Only critical hooks run (session start/end)
- **standard**: All recommended hooks (formatting, quality gates, reminders)
- **strict**: All hooks including blocking dev server checks

Set `ECC_DISABLED_HOOKS` to comma-separated hook IDs to disable specific hooks.

Example: `ECC_DISABLED_HOOKS=post:edit:format,post:edit:typecheck`
<!-- END ECC RULES: hooks -->
