# ReelBot — Project Context

## What It Does
Instagram Reel -> Business Strategy Pipeline. Receives reel URLs via Telegram bot or API, downloads video, transcribes audio, analyzes with LLM for business insights, generates implementation plans with concrete tasks, and executes automatable tasks.

## Stack
- **Runtime**: Python 3.11, FastAPI, uvicorn
- **LLM**: OpenRouter (Kimi K2.5 primary, Gemini Flash for similarity)
- **Bot**: Telegram bot — notification-only (sends title + recommended action + link to web panel)
- **Web UI**: Interactive control panel for plan review, task selection, approval, and feedback
- **Hosting**: Coolify on VPS (76.13.29.110), deploy via API
- **Storage**: Local filesystem (plans/ directory with JSON metadata + HTML views)

## Capabilities
- Video download + audio extraction (yt-dlp, ffmpeg)
- Whisper transcription (via API)
- Vision analysis (keyframe extraction at 512px + LLM vision)
- Carousel/image post analysis (OCR + vision)
- **Tiered plans (L1/L2/L3)**: Note it (0.25h) / Build it (0.5-2h) / Go deep (2-8h)
- **Web control panel**: task checkboxes, optional notes, approve selected/skip/feedback (good/bad/partial + comment)
- Plan generation with cost tracking
- Similarity detection between new reels and existing plans
- **Execution engine**: auto-executes approved tasks — sales_script, content drafts, n8n specs, knowledge_base notes
- **Knowledge base**: persistent insight storage with search/filter API (`/knowledge/`)
- Relevance scoring calibrated (0.85-0.95 baseline)
- Multi-project insight distribution (routes insights to tfww, ddb, gnomeguys, etc.)

## Current Status
- **Deployed and running** on production
- Pipeline: reel URL -> download -> transcribe -> analyze -> tiered plan -> Telegram notification -> web control panel
- Telegram simplified: 3-line notification (title + recommended action + link), no inline buttons
- Execution handlers: sales_script (auto), content drafts (auto), n8n specs (auto), knowledge_base (auto), code tasks (logged)
- Auto-deploy: GitHub Actions on push to main → Coolify API
- n8n webhook: fires on plan approval → `N8N_EXECUTION_WEBHOOK`
- Agent loop: `scripts/agent_loop.py` → systemd service on OpenClaw VPS (217.216.90.203)

## API Endpoints
- POST /api/reel — Submit reel URL for processing
- GET /plans/ — List all plans
- GET /plans/approved — Approved plans for execution
- GET /plans/{id}/view — HTML plan view (web control panel)
- GET /plans/{id} — Plan metadata JSON
- GET /plans/{id}/tasks — Task list with status + tool_data (for agents)
- POST /plans/{id}/approve — Approve selected tasks (accepts `selected_tasks` + `notes`)
- POST /plans/{id}/skip — Skip a plan
- POST /plans/{id}/feedback — Submit feedback (good/bad/partial + comment)
- PATCH /plans/{id}/status — Update plan status (triggers execution on approve)
- PATCH /plans/{id}/tasks/{index} — Mark task complete/failed (for agents)
- POST /plans/{id}/execute — Trigger plan execution
- GET /api/script — Full sales script JSON
- PUT /api/script/sections/{id} — Update script section
- GET /health — Health check
- GET /knowledge/ — List KB entries (filter by category/tag)
- GET /knowledge/search?q=... — Search KB entries
- GET /knowledge/context — Recent KB entries formatted for LLM prompts
- GET /costs — Cost breakdown page

## Authentication
- Write endpoints require `X-API-Key` header
- Read endpoints (GET) are public
- Key: `REELBOT_API_KEY` in master.env

## Agent Execution Flow
```
GET /plans/approved → GET /plans/{id}/tasks → execute → PATCH /plans/{id}/tasks/{index}
```
Agent script: `scripts/agent_loop.py` (single-pass or --watch mode)
