---
name: fireworks
description: Use when the user types /fireworks or asks to celebrate, test fireworks, or show a fireworks animation.
tools:
  - run_shell_command
---

# Fireworks Celebration

Run the fireworks animation immediately by executing:

```
node ~/.gemini/hooks/ecc/skill-fireworks.js --test ${SKILL_NAME:-celebration}
```

Replace `${SKILL_NAME}` with whatever the user wants to celebrate, or default to "celebration".

Do not explain anything before running the command. Just run it.
