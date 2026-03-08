# Comprehensive Examples of Prompt Improvement

This reference provides real-world examples showing the complete flow from vague prompts through research, question formulation, and execution.

## Table of Contents

- [Example Format](#example-format)
- [Vague Prompts (Research Required)](#vague-prompts-research-required)
- [Clear Prompts (Proceed Immediately)](#clear-prompts-proceed-immediately)
- [Bypass Prompts (Pass Through)](#bypass-prompts-pass-through)
- [Context-Dependent Prompts](#context-dependent-prompts)
- [Complex Multi-Question Scenarios](#complex-multi-question-scenarios)

## Example Format

Each example follows this structure:

1. **Original Prompt**: What the user said
2. **Evaluation**: Clarity assessment
3. **Research Plan** (if vague): What to investigate
4. **Research Findings** (if vague): What was discovered
5. **Questions Asked** (if vague): Conversational questions with options
6. **User Answers** (if vague): What user selected
7. **Execution**: How the request was fulfilled

## Vague Prompts (Research Required)

### Example 1: Generic Bug Fix

**Original Prompt:**
```
fix the bug
```

**Evaluation:**
- Target: missing (no file, function, or bug specified)
- Action: missing (what needs fixing?)
- Criteria: partial (bug fixed, but which bug?)
- Context: Check conversation history

**Conversation History Check:**
No recent error messages, no file viewing context.

**Decision:** RESEARCH REQUIRED

**Research Plan:**
```
1. Search for TODO/FIXME comments indicating known bugs
2. Check for failing tests
3. Look for recent git commits mentioning "fix" or "bug"
4. Search for try/catch blocks with console.error
```

**Research Execution:**
```bash
# Step 1
grep_search: "TODO|FIXME|BUG"
Results: 3 TODOs, 1 FIXME in auth.ts:89

# Step 2
glob: "**/*.test.ts"
run_shell_command: npm test
Results: 2 tests failing in test_auth.test.ts

# Step 3
run_shell_command: git log --grep="fix|bug" --oneline -10
Results: Recent commit "fix login redirect" 2 days ago

# Step 4
grep_search: "console.error|console.warn"
Results: Error logged in auth.ts:145 "Invalid token"
```

**Research Findings:**
- FIXME in auth.ts:89: "FIXME: Token validation is broken"
- 2 failing tests related to token validation
- Recent fix attempt for login redirect
- Error logging at auth.ts:145 for invalid tokens

**Questions Asked:**
```
I have a question to clarify your request:

**1. Which bug should be fixed?** (Bug target)
   a) Token validation (auth.ts:89) - FIXME comment indicates broken token validation. 2 failing tests in test_auth.test.ts related to this. Likely high priority.
   b) Login redirect (recent commit) - Recent commit 2 days ago attempted to fix login redirect. May have residual issues.
   c) Invalid token logging (auth.ts:145) - Errors being logged for invalid tokens. May be symptom of validation bug or separate issue.
   d) Other (please specify)
```

**User Answer:**
"Token validation (auth.ts:89)"

**Execution:**
Fix token validation in auth.ts:89, run tests to verify fix resolves the 2 failing tests.

---

### Example 2: Generic Refactoring Request

**Original Prompt:**
```
refactor the code to be better
```

**Evaluation:**
- Target: missing (what code?)
- Action: missing ("better" is subjective)
- Criteria: missing (what defines "better"?)
- Context: Check recent activity

**Context Check:**
User recently opened src/api/users.ts

**Research Plan:**
```
1. read_file src/api/users.ts to understand current state
2. Search for code quality issues (long functions, duplication)
3. Check for established patterns in similar files
4. Research Node.js/TypeScript refactoring best practices
```

**Research Findings:**
- users.ts is 450 lines, all logic in one file
- Other APIs (products) use service layer separation
- Industry pattern: Controller -> Service -> Repository
- Current code mixes validation, business logic, data access

**Questions Asked:**
```
I have a couple of questions to clarify your request:

**1. What aspect of the code should be improved?** (Improvement)
   a) Extract service layer - Create UserService class for business logic, matching ProductService pattern already used in products.ts. Separates concerns and improves testability.
   b) Split into multiple files - Break 450-line file into smaller modules (validation.ts, service.ts, controller.ts). Easier to navigate and maintain.
   c) Reduce function complexity - Refactor long functions (updateUser at 89 lines, createUser at 78 lines) into smaller, focused functions. Improves readability.
   d) Other (please specify)

**2. Should this follow the existing ProductService pattern?** (Pattern)
   a) Yes, match ProductService - Maintain consistency with existing codebase. Same architecture makes it easier for team to navigate.
   b) No, use different approach - Opportunity to establish new pattern if ProductService approach has issues.
   c) Other (please specify)
```

**User Answers:**
1. "Extract service layer"
2. "Yes, match ProductService"

**Execution:**
Extract UserService class following ProductService pattern, move business logic from users.ts to service/UserService.ts, keep controller thin.

---

### Example 3: Ambiguous Feature Request

**Original Prompt:**
```
add authentication
```

**Evaluation:**
- Target: partial (app-wide feature)
- Action: clear (add authentication)
- Criteria: missing (what type? what approach?)
- Context: Check project state

**Research Findings:**
- No existing authentication
- Express.js backend with REST API
- MongoDB database available
- Microservices architecture planned
- Must support mobile app (stateless preferred)

**Questions Asked:**
```
I have a few questions to clarify your request:

**1. Which authentication method should be implemented?** (Auth method)
   a) JWT with refresh tokens - Stateless authentication. Access token (short-lived) + refresh token (long-lived). Best for microservices and mobile apps. Industry standard for this use case.
   b) Session-based with MongoDB - Server-side sessions stored in MongoDB (connect-mongo). Simpler to implement, easier to invalidate. Works but less ideal for mobile/microservices.
   c) OAuth 2.0 integration - Delegate to third-party providers (Google, GitHub). Good user experience, but requires provider setup and internet connectivity.
   d) Other (please specify)

**2. Where should JWT tokens be stored on the client?** (Token store)
   a) HttpOnly cookies - Server sets cookie with HttpOnly flag. Protected from XSS attacks. Requires CSRF protection. Best for web apps.
   b) Authorization header - Client stores in memory, sends via Bearer token. Required for mobile apps. Client handles storage and sending.
   c) Both (web and mobile) - Support cookies for web, Authorization header for mobile. Maximum flexibility but adds complexity.
   d) Other (please specify)

**3. What should be included in the authentication scope?** (Scope - select all that apply)
   a) Login/register endpoints - POST /auth/register and POST /auth/login. Basic authentication flow.
   b) Password reset flow - Forgot password email workflow. Important for production but adds complexity.
   c) Role-based access control - User roles (admin, user, guest) with permission checking. Essential for most apps.
   d) Email verification - Verify email on registration. Prevents fake accounts but requires email service.
```

---

## Clear Prompts (Proceed Immediately)

### Example 4: Specific File and Action

**Original Prompt:**
```
Refactor the getUserById function in src/api/users.ts to use async/await instead of promise chains
```

**Evaluation:**
- Target: clear (getUserById in src/api/users.ts)
- Action: clear (refactor to async/await)
- Criteria: clear (no promise chains, use async/await)
- Context: Not needed

**Decision:** PROCEED IMMEDIATELY (no research or questions)

---

### Example 5: Specific Bug with Context

**Original Prompt:**
```
Fix the TypeError at line 145 in src/auth/login.ts where user.profile.name is undefined
```

**Evaluation:**
- Target: clear (login.ts:145)
- Action: clear (fix TypeError for user.profile.name)
- Criteria: clear (no TypeError, safe access)
- Context: Error description provided

**Decision:** PROCEED IMMEDIATELY

---

### Example 6: Clear Feature with Details

**Original Prompt:**
```
Add input validation to the registration form using Joi schema. Validate:
- Email (required, valid format)
- Password (required, min 8 characters, must include number and special char)
- Username (required, 3-20 characters, alphanumeric only)
```

**Decision:** PROCEED IMMEDIATELY

---

## Bypass Prompts (Pass Through)

### Example 7: Asterisk Bypass

**Original Prompt:**
```
* just add a quick comment explaining this function
```

**Detection:**
Bypass prefix `*` detected

**Action:**
Strip `*`, pass through as: "just add a quick comment explaining this function"

**Execution:**
Add comment without any evaluation or questions.

---

### Example 8: Slash Command

**Original Prompt:**
```
/commit
```

**Detection:**
Slash command format detected

**Action:**
Pass through unchanged

---

### Example 9: Hash Prefix (Memory)

**Original Prompt:**
```
# remember to use TypeScript strict mode for all new files
```

**Detection:**
Hash prefix `#` detected (memorize/note feature)

**Action:**
Pass through unchanged

---

## Context-Dependent Prompts

### Example 10: File Viewing Context Makes Clear

**Context:**
User recently opened src/components/LoginForm.tsx

**Prompt:**
```
refactor this to use hooks
```

**Evaluation:**
- Target: clear (LoginForm.tsx from file view context)
- Action: clear (refactor to hooks)

**Decision:** PROCEED IMMEDIATELY

---

### Example 11: Recent Error Provides Context

**Previous Message:**
```
Error: ECONNREFUSED: Connection refused at 127.0.0.1:5432
```

**Current Prompt:**
```
fix this connection error
```

**Decision:** PROCEED IMMEDIATELY (error message provides all details)

---

### Example 12: Ongoing Discussion Provides Context

**Message History:**
```
User: "Should I use Prisma or TypeORM for the database?"
Agent: "Prisma has better TypeScript support and migration tooling..."
User: "ok let's go with Prisma"
```

**Current Prompt:**
```
set it up
```

**Decision:** PROCEED (context makes this clear - implement Prisma setup)

---

## Complex Multi-Question Scenarios

### Example 13: Major Feature with Multiple Unknowns

**Original Prompt:**
```
implement caching
```

**Research Findings:**
- No current caching
- Slow endpoints: /api/products (500ms avg), /api/users (200ms avg)
- Redis installed but not configured
- Product catalog rarely changes (good cache candidate)
- User data changes frequently (poor cache candidate)

**Questions Asked:**
```
I have a few questions to clarify your request:

**1. What should be cached?** (Cache target - select all that apply)
   a) Product catalog (/api/products) - Currently 500ms response time. Products change infrequently (good cache candidate). High traffic endpoint.
   b) User profiles (/api/users/:id) - Currently 200ms response time. Profile data changes occasionally. Moderate traffic.
   c) Database queries - Cache at ORM level for all database queries. Broadest impact but requires careful invalidation.
   d) Other (please specify)

**2. Which caching strategy should be used?** (Strategy)
   a) Redis with TTL - External cache with time-to-live expiration. Redis already installed. Best for distributed systems. Standard approach.
   b) In-memory with node-cache - Simple in-process caching. Fast but not shared across instances. Good for single-server deployments.
   c) Redis with cache invalidation - Active invalidation on data changes. Most complex but most accurate. Requires event hooks on updates.
   d) Other (please specify)

**3. What should the cache TTL (time-to-live) be?** (TTL)
   a) 5 minutes - Aggressive caching. Data can be stale up to 5 minutes. Best for very static data.
   b) 1 minute - Balanced approach. Reduces load while keeping data relatively fresh. Good default.
   c) 30 seconds - Conservative caching. Minimal staleness but less performance benefit. Use for semi-dynamic data.
   d) Other (please specify)
```

---

## Summary: Decision Patterns

### Proceed Immediately If:
- Specific file and function mentioned with clear action
- Error message provides full context
- File viewing context clarifies ambiguous "this"
- Recent conversation establishes clear decisions
- All evaluation criteria pass

### Research and Ask If:
- Generic action verbs ("fix", "improve", "refactor") without target
- No file or component mentioned
- Multiple valid approaches
- Architectural decisions needed
- Configuration choices required

### Pass Through If:
- Bypass prefix detected (`*`, `/`, `#`)
- User explicitly opted out of evaluation

These examples demonstrate the spectrum from clear to vague and show how research findings directly inform specific, actionable questions.
