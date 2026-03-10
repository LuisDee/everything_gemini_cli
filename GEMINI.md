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
| strategic-compact | Context compaction at logical intervals |
| iterative-retrieval | Progressive context retrieval |
| python-testing | pytest, TDD, fixtures, mocking |
| cost-aware-llm-pipeline | LLM cost optimization patterns |
| e2e-testing | Playwright E2E testing |
| eval-harness | Eval-driven development framework |
| content-hash-cache-pattern | SHA-256 content hash caching |
| verification-loop | Comprehensive verification system |
| search-first | Research-before-coding workflow |
| agentic-engineering | Eval-first execution and decomposition |
| plankton-code-quality | Write-time code quality enforcement |
| ai-first-engineering | AI agent engineering operating model |
| continuous-agent-loop | Autonomous agent loops with quality gates |
| continuous-learning | Extract patterns from sessions |
| regex-vs-llm-structured-text | Regex vs LLM decision framework |
| ui-ux-pro-max | Design intelligence: 67 styles, 96 palettes, 57 fonts, BM25 search |
<!-- END ECC RULES: skills -->

<!-- BEGIN ECC RULES: ambient-patterns -->
# Ambient Best Practices (always active)

These patterns apply to ALL code written. Full references in `skills/*/SKILL.md`.

## Coding Standards (TS/JS/React/Node)
- Descriptive names; no single-letter variables
- Spread operator for immutability; never mutate objects/arrays directly
- Promise.all for parallel async; functional setState `prev => ...`
- No `any` type; use proper TypeScript interfaces
- Early returns to avoid nesting; guard clauses at function start
- Memoize expensive computations (useMemo/useCallback) only when profiled

## Backend Patterns (Node/Express/Next.js)
- Repository pattern for data access; service layer for business logic
- Prevent N+1 queries: batch fetch, never query in loops
- Cache with Redis (cache-aside pattern); set TTL on all cached data
- Custom ApiError with status codes; centralized error handler
- Retry with exponential backoff for external APIs; max 3 retries
- Select only needed columns; never `SELECT *` in production

## Frontend Patterns (React/Next.js)
- Composition over inheritance; build from smaller reusable pieces
- Custom hooks for reusable logic; prefix with `use`
- Lazy load heavy components with React.lazy + Suspense
- Virtualize long lists (1000+ items); debounce search inputs (500ms)
- Error boundaries around routes/features; Context + useReducer for complex state
- Keyboard navigation + ARIA attributes for accessibility

## Python Patterns
- EAFP not LBYL: use try/except, not if-checks before operations
- Type hints on all function signatures; modern syntax (`list[str]` not `List[str]`)
- Context managers (`with`) for all resources; never manual open/close
- Dataclasses for data containers; `is None` not `== None`
- Exception chaining: `raise NewError() from original`; no bare `except:`
- Protocol-based duck typing; async/await for I/O, multiprocessing for CPU

## API Design (REST)
- Plural nouns, kebab-case URLs, no verbs: GET /api/users not /getUsers
- Correct HTTP methods: GET read, POST create, PUT replace, PATCH update, DELETE
- Consistent error format with code, message, field-level details
- Cursor pagination for large datasets; offset for small/admin
- Bearer tokens in Authorization header; never API keys in URLs
- Rate limit with 429 + X-RateLimit headers + Retry-After

## PostgreSQL Patterns
- Index foreign keys; unindexed FKs cause slow JOINs
- `CREATE INDEX CONCURRENTLY` on existing tables; avoids write locks
- Composite indexes: equality columns first, then range columns
- Use `timestamptz`, `text`, `numeric` for money; cursor pagination over OFFSET
- Row Level Security: wrap auth.uid() in SELECT for index usage
- Monitor pg_stat_statements; vacuum tables with high dead tuple count

## Docker Patterns
- Multi-stage Dockerfiles: deps, build, production (smallest final image)
- Run as non-root user; pin specific image tags, never `:latest`
- .dockerignore to exclude node_modules, .git, tests
- Named volumes for persistence; bind mounts for dev hot reload only
- Health checks in Dockerfile and compose; env vars for config

## Deployment Patterns
- Rolling deploy default; blue-green for critical; canary for risky changes
- Validate env vars at startup with schema; fail fast on missing config
- Health endpoint: 200 liveness, 503 degraded with dependency status
- CI/CD: lint, typecheck, test, build, deploy staging, smoke tests, production
- Rollback plan: previous image tagged; migrations reversible or forward-only

## Database Migrations
- Every schema change is a migration; never alter production manually
- Migrations immutable once deployed; create new migration for fixes
- Schema and data migrations separate; DDL and DML never in same file
- Add columns nullable or with default; NOT NULL without default locks table
- Zero-downtime: expand (add new), migrate (dual-write), contract (remove old)
<!-- END ECC RULES: ambient-patterns -->

<!-- BEGIN ECC RULES: hooks -->
# Hook Profile System

Set `ECC_HOOK_PROFILE` env var: `minimal` | `standard` (default) | `strict`

- **minimal**: Only critical hooks run (session start/end)
- **standard**: All recommended hooks (formatting, quality gates, reminders)
- **strict**: All hooks including blocking dev server checks

Set `ECC_DISABLED_HOOKS` to comma-separated hook IDs to disable specific hooks.

Example: `ECC_DISABLED_HOOKS=post:edit:format,post:edit:typecheck`
<!-- END ECC RULES: hooks -->
