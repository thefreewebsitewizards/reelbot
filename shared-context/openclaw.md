# OpenClaw — Project Context

## What It Does
Autonomous AI agent ("Claw") running 24/7 on a Contabo VPS, connected to Discord as a personal Life OS assistant. Handles scheduled briefings, responds to chat, routes across multiple LLM providers, and dispatches Claude Code for coding tasks.

## Stack
- **Runtime**: Node.js v22 on Ubuntu 24.04 (6 vCPU, 12GB RAM, 193GB NVMe)
- **Other key tech**: OpenClaw v2026.2.26 (binary behind — config touched by v2026.3.1, v2026.3.2 available), Ollama (llama3.2:3b for free heartbeats), systemd user service, Discord.js bot, AgentMail

## Capabilities
- Discord bot (@openclaude) on "Life OS" server — 25 channels, 7 categories, responds without @mention
- Multi-model routing: Codex 5.3 (primary, ChatGPT Plus OAuth), Kimi K2.5 + MiniMax M2.5 (OpenRouter fallbacks)
- Scheduled cron: healthcheck (*/15m), daily backup (3am), workspace git snapshots (3:05am), update check (4am)
- Local Ollama inference for heartbeats (free, 1h interval, 08:00-22:00 ET)
- AgentMail inbox (claw-lifeos@agentmail.to) for email
- 21 workspace skills (5 original + 5 custom + 11 ClawHub)
- Claude Code CLI on VPS for coding dispatch (Max plan OAuth, 2 concurrent sessions)
- Telegram provider also running (appeared post-config touch)

## Current Status
- **Gateway**: Active, running 6+ days, Discord connected and self-healing
- **Version mismatch**: Binary is v2026.2.26, config says v2026.3.1 touched it, v2026.3.2 available — needs update
- **Missing cron jobs**: Morning briefing (8am), evening summary (9pm), weekly review (Sun 10am), ML-ops analysis — all disappeared from crontab
- **Logging broken**: No log files being written to /tmp/openclaw-1000/ since March 2 (only stale lock file)
- **Workspace git snapshots**: Working (latest March 8)
- **Doctor status**: Unknown since version mismatch appeared

## Integration Points
- **Discord**: Guild 1476534972662812743, bot ID 1476533719472013393, owner-only allowlist
- **SSH**: Key auth at 217.216.90.203 (users: openclaw, root)
- **Gateway API**: loopback:18789 with token auth (SSH tunnel for remote access)
- **OpenRouter API**: For Kimi K2.5 and MiniMax M2.5 models
- **ChatGPT Plus OAuth**: For Codex 5.3 primary model
- **AgentMail API**: Inbox claw-lifeos@agentmail.to
- **Ollama**: loopback:11434 for local inference
- **Claude Code CLI**: Dispatched via `claude -p --permission-mode dontAsk --max-turns 20`
- **Mission Control**: React+Express dashboard (separate subproject, not deployed as service yet)
