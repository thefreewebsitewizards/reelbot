# Shared Cross-Project Context

This directory contains status files for each Claude Code project under openclaw.
ReelBot's analysis and planning prompts read from these files dynamically to understand
the full business context when generating plans.

## How It Works

1. Each project has a `<project-name>.md` file here describing what it does, its stack, capabilities, and current status
2. ReelBot's `src/utils/shared_context.py` reads all `.md` files and injects them into LLM prompts
3. When a project's capabilities change, update its file here so plans stay accurate

## Files

- `aias.md` — AI Appointment Setter
- `ddb.md` — Dylan Does Business (personal brand)
- `ghl-fix.md` — GoHighLevel fixes/config
- `n8n-automations.md` — n8n workflow automations
- `reelbot.md` — Instagram Reel analysis pipeline (this system)
- `tfww.md` — The Free Website Wizards

## Updating

Any Claude Code session can update its project file:
```bash
# From any project session, write updated context:
cat > ~/projects/openclaw/.shared-context/<project-name>.md << 'EOF'
# Project Name — Project Context
## What It Does
...
## Stack
...
## Capabilities
...
## Current Status
...
EOF
```

Keep the format consistent: H1 title, then sections for What It Does, Stack, Capabilities, Current Status.
