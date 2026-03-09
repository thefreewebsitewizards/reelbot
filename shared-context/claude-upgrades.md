# Claude Upgrades — Project Context

## What It Does
Optimizes Claude Code configuration across the OpenClaw project ecosystem — reducing token overhead, consolidating rules/skills, scoping MCP servers, and improving session continuity via handoff documents.

## Stack
- **Runtime**: WSL2 Ubuntu 24.04, Node 20, Claude Code CLI (Opus 4.6, Max plan)
- **Other key tech**: GSD plugin, Superpowers plugin, Everything Claude Code plugin, Claude Mem plugin, gws CLI (Google Workspace)

## Capabilities
- Token overhead analysis and reduction (rules, skills, MCP, memory files)
- Rules consolidation (`~/.claude/rules/standards.md` — single file, ~1.4k tokens)
- MCP server scoping (global vs project-level in `.claude/settings.json`)
- Skill scoping (moved n8n skills to aias project scope)
- Context monitor hook (`gsd-context-monitor.js`) — auto-triggers handoff at 75% context
- Handoff skill (`~/.claude/skills/context-handoff/SKILL.md`) — generates HANDOFF.md for session continuity
- gws MCP for Gmail/Calendar (authenticated, scoped to openclaw project)
- Playwright CLI installed and auto-approved for browser automation
- Context7 MCP globally available for documentation lookups

## Current Status
- **Working**: All optimizations applied and verified. Context overhead reduced from ~55k to ~19k tokens. gws authenticated (dylan@thefreewebsitewizards.com). Playwright CLI functional with Chromium.
- **In progress**: None — all planned work complete.
- **Known issues**: ECC plugin loads ~100+ skill descriptions for unused languages (Swift, Go, C++, etc.) — can't selectively disable. Hook P95 latency ~250ms (acceptable).

## Integration Points
- `~/.claude/settings.json` — global Claude Code settings (hooks, permissions, plugins)
- `~/.claude.json` — app state, MCP servers, project configs
- `~/.claude/rules/standards.md` — shared engineering standards for all projects
- `~/.claude/hooks/gsd-context-monitor.js` — PostToolUse hook for all sessions
- `~/.claude/hooks/gsd-statusline.js` — status line for all sessions
- `~/.config/gws/` — Google Workspace CLI credentials (encrypted)
- `~/projects/openclaw/.claude/settings.json` — project-scoped gws MCP config
- `~/projects/aias/.claude/skills/` — project-scoped n8n skills
