# Question Patterns for Effective Clarification

This reference provides templates, patterns, and best practices for formulating clarifying questions that are grounded in research and lead to actionable answers.

## Table of Contents

- [Question Construction Principles](#question-construction-principles)
- [Question Format](#question-format)
- [Question Templates by Category](#question-templates-by-category)
- [Number of Questions Guidelines](#number-of-questions-guidelines)
- [Option Generation Best Practices](#option-generation-best-practices)
- [Common Pitfalls](#common-pitfalls)

## Question Construction Principles

### Core Principles

1. **Ground in Research**: Every option must come from actual findings
   - Codebase exploration results
   - Documentation references
   - Web search for best practices
   - Git history for patterns

2. **Be Specific**: Avoid generic options
   - Bad: "Use a different approach"
   - Good: "Use JWT tokens with HttpOnly cookies"

3. **Provide Context**: Explain trade-offs in descriptions
   - Why this option exists
   - What it implies
   - When it's appropriate

4. **Stay Focused**: One decision point per question
   - Bad: "Which file and what approach?"
   - Good: "Which file?" (separate question for approach)

5. **Enable Choice**: 2-4 options per question
   - Fewer than 2: Not a choice
   - More than 4: Overwhelming
   - "Other" should always be available

### Question Quality Checklist

Before formulating questions, verify:

- [ ] Completed research phase with documented findings
- [ ] Each option based on actual research (not assumptions)
- [ ] Each option is specific and actionable
- [ ] Context/trade-offs included in descriptions
- [ ] Questions are independent (can be answered in any order)
- [ ] Total questions: 1-6 based on complexity

## Question Format

### Conversational Format

Present questions directly to the user with numbered options:

```
I have a few questions to clarify your request:

**1. Which file should be modified?** (Target file)
   a) src/auth/login.ts - Main login handler with authentication logic (currently 245 lines)
   b) src/auth/middleware.ts - Authentication middleware used by all protected routes (89 lines)
   c) src/auth/session.ts - Session management and validation utilities (156 lines)
   d) Other (please specify)

**2. Which approach should we use?** (Approach)
   a) JWT with HttpOnly cookies - Prevents XSS, requires CSRF protection
   b) Session-based with Redis - Simpler, easier to invalidate
   c) Other (please specify)
```

### Field Guidelines

**Question text:**
- Must end with `?`
- Should be conversational and clear
- Include context from research if helpful
- Examples:
  - "Which authentication approach should we implement?"
  - "Where should the validation logic be added?"
  - "What scope should this refactoring cover?"

**Header/label:**
- Short descriptive label in parentheses
- Examples: (Auth method), (Target file), (Scope), (Approach)

**Options:**
- Minimum 2, maximum 4 options plus "Other"
- Each must have a label and description

**Label:**
- 1-5 words typically
- Specific and scannable

**Description:**
- Explain what this option means
- Include trade-offs or implications
- Provide context for decision-making

## Question Templates by Category

### Target Identification Questions

**When:** Unclear which file, function, or component to modify

**Template 1: File Selection**
```
**1. Which file should be modified?** (Target file)
   a) src/auth/login.ts - Main login handler with authentication logic (currently 245 lines)
   b) src/auth/middleware.ts - Authentication middleware used by all protected routes (89 lines)
   c) src/auth/session.ts - Session management and validation utilities (156 lines)
   d) Other (please specify)
```

**Template 2: Function/Method Selection**
```
**1. Which function needs the changes?** (Function)
   a) validateUser() - Validates user credentials against database (auth.ts:45)
   b) authenticateToken() - Verifies JWT token signature and expiration (auth.ts:89)
   c) refreshSession() - Extends active session duration (auth.ts:134)
   d) Other (please specify)
```

### Approach/Implementation Questions

**When:** Target is clear, but implementation approach is ambiguous

**Template 1: Technical Approach**
```
**1. Which authentication approach should we implement?** (Auth method)
   a) JWT with HttpOnly cookies - Store JWT in HttpOnly cookies. Prevents XSS attacks, simpler client-side code. Requires CSRF protection.
   b) JWT in Authorization header - Client stores JWT in memory, sends in Bearer token. More flexible for mobile apps, requires client-side token management.
   c) Session-based with Redis - Server-side sessions stored in Redis. Traditional approach, easier to invalidate, requires session store infrastructure.
   d) Other (please specify)
```

### Scope Questions

**When:** Unclear how much work should be done

**Template 1: Feature Scope**
```
**1. What scope should this refactoring cover?** (Scope)
   a) Single function only - Refactor just getUserById(). Minimal change, quick to implement and test.
   b) Entire UserRepository class - Refactor all user data access methods (8 functions). Consistent patterns across class.
   c) All repository classes - Apply pattern to UserRepository, ProductRepository, OrderRepository (3 classes, 24 functions). Codebase-wide consistency.
   d) Other (please specify)
```

### Priority/Order Questions

**When:** Multiple tasks or unclear which to tackle first

### Configuration Questions

**When:** Implementation requires configuration choices

## Number of Questions Guidelines

### 1-2 Questions: Simple Clarification

**Use when:**
- Single point of ambiguity
- Binary or ternary choice
- Target identification only

### 3-4 Questions: Moderate Complexity

**Use when:**
- Multiple independent decisions needed
- Approach and scope both unclear
- Configuration plus implementation questions

### 5-6 Questions: Complex Scenarios

**Use when:**
- Major feature with multiple architectural decisions
- Multiple aspects needing clarification
- Configuration, approach, scope, and priority all unclear

**Important:** Only use 5-6 questions when truly necessary. Most scenarios should use 1-4 questions.

## Option Generation Best Practices

### Grounding Options in Research

**Bad (Assumption-Based):**
```
a) Use MongoDB - NoSQL database, good for flexibility
```

**Good (Research-Grounded):**
```
a) Use MongoDB - NoSQL database. Project already uses MongoDB for user data (see db/connection.ts). Consistent with existing stack.
```

### Providing Actionable Context

**Bad (Vague):**
```
a) Refactor approach - Better way to organize code
```

**Good (Specific):**
```
a) Extract to service layer - Move business logic from controllers to UserService class. Follows repository pattern already used in OrderService and ProductService.
```

### Including Trade-offs

**Bad (One-Sided):**
```
a) Microservices architecture - Modern, scalable approach
```

**Good (Balanced):**
```
a) Microservices architecture - Split into auth-service and user-service. Better scaling and independence, but adds deployment complexity. Team has Docker expertise.
```

### Using Codebase Evidence

**Research findings inform options:**

```
Research Results:
- Found 3 API clients: src/api/rest-client.ts, src/api/graphql-client.ts, src/api/websocket-client.ts
- rest-client.ts has timeout config (line 23: timeout: 30000)
- graphql-client.ts missing timeout (potential bug)
- websocket-client.ts uses different pattern (reconnect logic)
```

**Generated question:**
```
**1. Which API client needs timeout configuration?** (API client)
   a) REST client (src/api/rest-client.ts) - Already has 30s timeout. Update existing configuration.
   b) GraphQL client (src/api/graphql-client.ts) - Missing timeout configuration. Likely the source of hanging requests.
   c) WebSocket client (src/api/websocket-client.ts) - Uses reconnect pattern instead of timeout. Different approach needed.
   d) Other (please specify)
```

## Common Pitfalls

### Pitfall 1: Generic Options

**Bad:**
```
a) Best practice approach - Use industry standard methods
```

**Fix:**
```
a) Repository pattern with dependency injection - Separate data access into UserRepository, injected via constructor. Used in OrderService (see src/services/order.service.ts:15).
```

### Pitfall 2: Too Many Options

**Bad:** 6+ options per question

**Fix:** Narrow to 2-4 most relevant options based on research. If more than 4, create multiple questions or categorize.

### Pitfall 3: Leading Questions

**Bad:**
```
Should we use the superior JWT approach?
  a) Yes, JWT
  b) No, sessions
```

**Fix:**
```
Which authentication mechanism should be implemented?
  a) JWT tokens - Stateless, scales horizontally. Client manages tokens. Trade-off: harder to invalidate.
  b) Server-side sessions - Stateful, easier to invalidate. Server manages state. Trade-off: requires shared session store.
```

### Pitfall 4: Compound Questions

**Bad:** "Which library and what configuration should be used?"

**Fix:** Separate into two questions — one for library, one for configuration.

### Pitfall 5: Asking Without Research

**Bad:** Options based on general knowledge

**Fix:** Research first, then generate options based on findings.

## Summary Checklist

Before presenting questions:

- [ ] Completed research phase with documented findings
- [ ] Each option grounded in research (not assumptions)
- [ ] Each option is specific and actionable (not generic)
- [ ] Descriptions include context and trade-offs
- [ ] Questions are focused (one decision per question)
- [ ] Using 1-6 questions based on complexity
- [ ] Each question has 2-4 options plus "Other"
- [ ] Question ends with `?`

**Remember:** The goal is clarity through specificity. Every option should be traceable back to research findings. Generic or assumed options undermine trust and lead to poor decisions.
