# Tiered Auto-Execution System

## Problem
Plans get approved in Telegram but nothing executes automatically. The pipeline stops at "approved" status and waits for manual action.

## Solution
Three-tier execution system that defaults to the fastest executor (Claude Code), falls back to OpenClaw for async work, and escalates to Dylan only when human judgment/money is needed.

## Architecture

```
Reel processed -> Plan created (status: review)
                       |
          User approves in Telegram
                       |
          _trigger_execution() fires
                       |
          Executor reads plan tasks
                       |
          For each task:
            Can Claude Code do it? -> Execute immediately
              (code, configs, scripts, API calls, deploy, VPS)
            Needs human? -> Telegram notification to Dylan
              (spend money, creative judgment, real-world action)
                       |
          All auto tasks done -> report results via Telegram
          Human tasks -> queued with reminders
```

### Async fallback (OpenClaw cron)
When no Claude Code session is active, OpenClaw picks up approved plans via a cron job. It can:
- Read plan files from the shared filesystem
- Execute simple tasks (file writes, API calls)
- Notify Dylan via Discord for human-required tasks

## Tier Classification

Tasks classified by their `tools` and `requires_human` fields:

**Auto-executable (Claude Code / OpenClaw):**
- `claude_code` — write/edit code in any project
- `n8n` — create/update workflow JSONs
- `sales_script` — PUT /api/script/sections/{id}
- `website` — create content, configs, HTML/CSS
- `ghl` — automation configs, pipeline setup docs
- `meta_ads` — draft ad copy (not spend)
- `telegram` — send messages via bot
- `deploy` — git push + Coolify rebuild via SSH
- `vps` — SSH commands on either server

**Human-required:**
- `requires_human == True` — money, judgment, external commitments
- Notified via Telegram with task details and "Done" button

## Execution Flow

1. Plan approved -> `_trigger_execution()` already writes to `_approved_queue.json`
2. Executor picks up plan, reads tasks from plan.md + metadata
3. For each task (respecting dependency order):
   a. If `requires_human`: send Telegram notification, skip
   b. Else: classify by tool type, execute
   c. Report result (success/failure) per task
4. After all auto tasks: update plan status, send summary to Telegram
5. If human tasks remain: plan stays `in_progress` until Dylan marks them done

## What Changes

| File | Change |
|------|--------|
| `src/services/executor.py` | Real execution engine — parse tasks, classify, execute, report |
| `src/utils/plan_manager.py` | Wire approval trigger to executor |
| `src/services/telegram_bot.py` | Execution status notifications, human task buttons |
| `scripts/execution_watcher.py` | Call real executor instead of just status transition |
| `src/utils/insight_distributor.py` | Add openclaw routing for system upgrade insights |
| `src/utils/design_insights.py` | Delete (dead code, replaced by insight_distributor) |

## Cleanup

- Delete `src/utils/design_insights.py` (dead code)
- Unify `routing_target` (LLM output) with `CATEGORY_TO_TOPICS` — routing_target becomes the hint, category-based routing stays as the deterministic system
- Ensure all routed project folders exist before writing

## Not In Scope

- Full autonomous code generation (tasks report what to do, not auto-write arbitrary code yet)
- OpenClaw cron job setup (do after core executor works)
- Budget tracking for human-approved spending
