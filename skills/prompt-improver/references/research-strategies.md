# Research Strategies for Context Gathering

This reference provides systematic approaches for researching codebase context, best practices, and patterns before formulating clarifying questions.

## Table of Contents

- [Research Planning Framework](#research-planning-framework)
- [Codebase Exploration Strategies](#codebase-exploration-strategies)
- [Documentation Research](#documentation-research)
- [Web Research for Best Practices](#web-research-for-best-practices)
- [Conversation History Mining](#conversation-history-mining)
- [Tool Selection Guide](#tool-selection-guide)
- [Research Execution Patterns](#research-execution-patterns)

## Research Planning Framework

### Phase 1: Identify What's Unclear

Before researching, explicitly identify gaps:

**Target Gap:**
- "Which file/function needs modification?"
- "What component is involved?"

**Approach Gap:**
- "How should this be implemented?"
- "What pattern should be used?"

**Scope Gap:**
- "How much should be changed?"
- "What's included in this request?"

**Context Gap:**
- "What's the current state?"
- "What patterns exist already?"

### Phase 2: Create Research Plan

Create a research plan before executing. This ensures systematic investigation.

**Template:**
```
Research Plan for [Prompt Type]:
1. [What to research] - [Tool/approach]
2. [What to research] - [Tool/approach]
3. [What to research] - [Tool/approach]
```

**Example:**
```
Research Plan for "fix the bug":
1. Check conversation history for error messages - Review recent messages
2. Search for failing tests - grep_search for "failing", "error", "TODO"
3. Explore recent commits - Git log for problem areas
4. Identify patterns in similar code - read_file related files
```

### Phase 3: Execute Research

Systematically execute each research step, documenting findings.

### Phase 4: Document Findings

Summarize what you learned:
- Key files involved
- Existing patterns found
- Common approaches in the codebase
- Relevant best practices
- Constraints or requirements discovered

## Codebase Exploration Strategies

### Strategy 1: Pattern Discovery

**When to use:** Need to understand architecture, find similar implementations, or explore unknown territory

**Approach:**
- Map codebase structure
- Find similar implementations
- Understand architectural patterns
- Identify relevant components

**Example:**
```
Prompt: "find the bug"

Research:
1. Explore: "Find error handling patterns in authentication code"
2. Results: Discover auth.ts, middleware.ts, session.ts with different error patterns
3. Finding: Inconsistent error handling across auth files
```

### Strategy 2: Targeted File Search (glob)

**When to use:** Know what you're looking for (file type, name pattern)

**Common patterns:**
```bash
# Find all authentication-related files
**/*auth*.ts

# Find test files
**/*.test.ts
**/*.spec.ts

# Find configuration files
**/*config*.{json,yaml,yml}
**/.*rc

# Find documentation
**/*.md
**/README*
```

**Example:**
```
Prompt: "add tests"

Research:
1. glob: "**/*.test.ts" -> Find existing test files
2. Identify pattern: Tests colocated with source files
3. Finding: Use Jest, tests in __tests__/ directories
```

### Strategy 3: Content Search (grep_search)

**When to use:** Looking for specific code patterns, function calls, or keywords

**Effective searches:**
```bash
# Find authentication implementations
pattern: "authenticate|login|auth"

# Find TODOs and FIXMEs
pattern: "TODO|FIXME|XXX|HACK"

# Find error handling
pattern: "try.*catch|throw new|Error\\("

# Find specific function calls
pattern: "validateUser\\(|checkAuth\\("

# Find configuration usage
pattern: "process\\.env|config\\.|getConfig"
```

**Example:**
```
Prompt: "improve error handling"

Research:
1. grep_search: "try.*catch" with multiline mode
2. grep_search: "throw new Error"
3. Finding: 15 try/catch blocks, 8 throw different error types
4. Pattern: Some use custom errors (AuthError, ValidationError), some use generic Error
```

### Strategy 4: Architecture Understanding (read_file + Explore)

**When to use:** Need to understand how systems connect

**Approach:**
1. Start with entry points (index.ts, main.ts, app.ts)
2. Read key configuration files (package.json, tsconfig.json)
3. Explore directory structure
4. Read README.md and architecture docs

**Example:**
```
Prompt: "refactor the API"

Research:
1. read_file: package.json -> Express.js backend
2. read_file: src/index.ts -> Entry point, middleware setup
3. Explore: src/routes/ -> Route organization pattern
4. Finding: RESTful API with route/controller/service layers
```

### Strategy 5: Historical Context (Git Commands)

**When to use:** Understanding evolution, finding related changes

**Useful git commands via run_shell_command:**
```bash
# Recent commits
git log --oneline -20

# Commits affecting specific file
git log --oneline path/to/file

# Search commit messages
git log --grep="authentication" --oneline

# Find when function was added
git log -S "functionName" --oneline

# See recent changes
git diff HEAD~5..HEAD --stat
```

**Example:**
```
Prompt: "fix the recent regression"

Research:
1. Git log: Last 10 commits
2. Git log --grep="fix|bug": Recent bug fixes
3. Finding: Commit 3 days ago changed auth flow
4. Pattern: Regression likely in authentication changes
```

## Documentation Research

### Strategy 1: Local Documentation (read_file)

**Priority order:**
1. README.md at project root
2. docs/ directory
3. Package-specific READMEs (packages/*/README.md)
4. CONTRIBUTING.md
5. Architecture docs (.architecture/, docs/architecture/)
6. API documentation (docs/api/)

### Strategy 2: Package Documentation (read_file + WebFetch)

**When to use:** Understanding third-party library usage

**Approach:**
1. Read package.json for library versions
2. Check local docs or examples
3. Fetch official documentation if needed

### Strategy 3: Code Comments (grep_search)

**When to use:** Finding design decisions, warnings, constraints

**Patterns:**
```bash
# Find important comments
pattern: "NOTE:|WARNING:|IMPORTANT:|FIXME:"

# Find documentation comments
pattern: "/\\*\\*|@param|@returns"

# Find constraint notes
pattern: "must|require|cannot|constraint"
```

## Web Research for Best Practices

### Strategy 1: Current Best Practices (WebSearch)

**When to use:** Need current approaches, recent changes, industry standards

**Effective queries:**
```
# Framework-specific patterns
"React authentication best practices 2024"
"Express.js error handling patterns 2024"

# Library comparisons
"JWT vs session authentication comparison"
"Joi vs Zod validation library comparison"

# Implementation approaches
"implement rate limiting Node.js"
"database transaction patterns TypeScript"
```

### Strategy 2: Framework Documentation (WebFetch)

**When to use:** Need official guidance for frameworks in use

### Strategy 3: Common Architectures (WebSearch + WebFetch)

**When to use:** Implementing well-known patterns

## Conversation History Mining

### Strategy 1: Recent Context Review

**When to use:** Always (first step in research)

**Check for:**
- Error messages in recent messages
- File names mentioned
- Features discussed
- Decisions made
- Code shown or referenced

### Strategy 2: Topic Tracking

**When to use:** Understanding what user is working on

**Pattern:**
- Last 5-10 messages establish working context
- File views indicate focus area
- Previous questions show user intent

### Strategy 3: File View Context

**When to use:** User viewing specific file

## Tool Selection Guide

### Choosing the Right Tool

**Explore:**
- Broad exploration needed
- Understanding architecture
- Finding similar patterns
- Complex multi-step research

**glob:**
- Finding files by name pattern
- Known file types
- Specific naming conventions

**grep_search:**
- Searching code content
- Finding function calls
- Pattern matching
- TODO/FIXME discovery

**read_file:**
- Reading specific files
- Documentation review
- Configuration inspection
- Package.json analysis

**run_shell_command (git commands):**
- Historical context
- Recent changes
- Commit messages
- File history

**WebSearch:**
- Current best practices
- Industry standards
- Library comparisons
- Common solutions

**WebFetch:**
- Official documentation
- Specific documentation pages
- API references
- Tutorial content

### Multi-Tool Research Patterns

**Pattern 1: Architecture Discovery**
```
1. read_file: package.json (understand stack)
2. read_file: README.md (understand project)
3. Explore: Map architecture
4. glob: Find similar files
5. read_file: Representative files
```

**Pattern 2: Implementation Approach**
```
1. grep_search: Search for existing pattern
2. read_file: Example implementation
3. WebSearch: Best practices
4. WebFetch: Official docs
5. Synthesize: Combine findings
```

**Pattern 3: Bug Investigation**
```
1. Review: Conversation history for errors
2. grep_search: Search for error patterns
3. run_shell_command: Git log for recent changes
4. read_file: Affected files
5. Explore: Find related code
```

## Research Execution Patterns

### Pattern 1: Quick Research (1-2 tools)

**When:** Simple ambiguity, limited scope

**Example:**
```
Prompt: "add tests"

Research:
1. glob: "**/*.test.ts" -> Find test pattern
2. read_file: "src/__tests__/example.test.ts" -> See structure

Findings:
- Jest framework
- Tests in __tests__/ directories
- Pattern established
```

### Pattern 2: Moderate Research (3-4 tools)

**When:** Multiple unknowns, need pattern understanding

### Pattern 3: Comprehensive Research (5+ tools)

**When:** Major feature, architectural decision, complex implementation

### Research Documentation Template

After research, document findings:

```
## Research Findings for "[Prompt]"

**What was unclear:**
- [List ambiguities]

**Research executed:**
1. [Tool] - [What searched] - [Key finding]
2. [Tool] - [What searched] - [Key finding]

**Key discoveries:**
- [Important finding 1]
- [Important finding 2]
- [Pattern identified]
- [Constraint discovered]

**Options identified:**
1. [Option A] - [From research source]
2. [Option B] - [From research source]
3. [Option C] - [From research source]

**Questions to ask:**
- [Question 1 based on findings]
- [Question 2 based on findings]
```

## Summary Checklist

Before asking questions:

- [ ] Created research plan
- [ ] Checked conversation history for context
- [ ] Explored codebase for existing patterns
- [ ] Searched for similar implementations
- [ ] Reviewed relevant documentation
- [ ] Researched best practices (if needed)
- [ ] Documented findings
- [ ] Generated specific options from research
- [ ] Verified each option is grounded in findings
- [ ] Marked research phase complete

**Critical Rules:**
1. NEVER skip research phase
2. ALWAYS ground questions in findings
3. NEVER assume based on general knowledge
4. ALWAYS use conversation history first
5. DOCUMENT research findings before asking

Research is the foundation of effective clarification. The quality of your questions depends entirely on the thoroughness of your research.
