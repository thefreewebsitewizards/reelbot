# Session Handoff — 2026-03-07 (Session 2)

## Project Overview
- Instagram Reel → Business Strategy Pipeline (FastAPI + Telegram bot + OpenRouter LLM)
- Key ref: `CLAUDE.md` for full architecture, commands, and execution rules

## Completed This Session

### Dashboard + Deployment + Cost Tracking (all done)
1. **Cost Tracking** — `src/services/llm.py`: `chat()` returns `ChatResult` with text + tokens + cost. `MODEL_PRICING` dict, `estimate_cost()`. All callers updated to return `(result, ChatResult)` tuples. `CostBreakdown`/`LLMCallCost` models in `src/models.py`. Costs accumulated in `reel.py` and `telegram_bot.py`, persisted in `metadata.json` and `_index.json`, shown in Telegram summary and HTML cost table.

2. **Per-step model overrides** — `src/config.py` has `openrouter_model_analysis`, `openrouter_model_plan`, etc. `llm.py:get_model_for_step()` resolves per-step model. Default is now `gemini-2.5-pro` for quality, only similarity uses Flash.

3. **Dashboard** — `static/dashboard.html` (dark theme, search, status filter, category grouping). `src/routers/dashboard.py` serves `GET /` with stats + plan cards. `src/main.py` registers dashboard router + mounts `/static`.

4. **Action Buttons** — `static/plan_view.html` has Approve/Reject/Complete/Dashboard buttons with `fetch()` to `PATCH /plans/{reel_id}/status`. `plan_writer.py:_build_action_buttons()` renders them.

5. **Deployment** — `docker-compose.yml` updated: nginx replaced with `cloudflared` for Cloudflare Tunnel. `DEPLOY.md` created with step-by-step guide.

6. **Execution Watcher** — `scripts/execution_watcher.py`: polls `_approved_queue.json` every 60s, transitions plans to `in_progress`. `plan_manager.py` POSTs to n8n webhook on approval. `config.py` has `n8n_execution_webhook`.

### Tests
- 24 passing (`python3 -m pytest tests/test_pipeline.py -v`)

## Key Decisions
- Default model changed to `google/gemini-2.5-pro` (~$0.08-0.15/reel) — user wants best quality, cost is not a concern
- Only similarity check stays on Flash (just text comparison, no reasoning needed)
- Cloudflare Tunnel instead of nginx+certbot (simpler, no port exposure)
- Dashboard uses same `{{placeholder}}` template pattern as plan_view.html (no Jinja2 dep)

## Next Feature: Plan Routing to Sister Folders

### What Dylan wants
Plans should be routed to the correct sister project folder based on content:
- Claude upgrades → `../claude-upgrades/`
- OpenClaw upgrades → `../` (openclaw root or relevant subfolder)
- Social media / DDB content → `../ddb/`
- Business ops (email, sales, marketing) → `../tfww/` (creating subfolders as needed)
- n8n automations → `../n8n-automations/`
- GHL stuff → `../ghl-fix/` or similar

**Not the full plan** — just a blurb + link to the web page (`https://reel-bot.leadneedleai.com/plans/{reel_id}/view`).

### Sister folders (at `/home/gamin/projects/openclaw/claude-code-projects/`):
- `aias`, `claude-upgrades`, `ddb`, `ghl-fix`, `masters-week`, `n8n-automations`, `pixel-agents`, `tfww`, `vibe-marketing`

### Implementation approach
1. Add routing rules — map `analysis.category` + keywords to target folder
2. After `write_plan()`, create a small `.md` blurb file in the target sister folder
3. Blurb contains: title, theme, summary, link to web view
4. May need a new field on `AnalysisResult` or use existing `category` + `business_applications[].target_system`
5. Consider having the LLM suggest the routing target during analysis

### Key files to modify
- `src/utils/plan_writer.py` — add routing logic after plan is written
- `src/models.py` — possibly add `routing_target` field
- `src/config.py` — sister folder base path
- Could also be a new `src/utils/plan_router.py`

## Context Notes
- Tests: `python3 -m pytest tests/test_pipeline.py -v` — 24 passing
- All imports verified: `python3 -c "from src.main import app"`
- `.env` overrides config defaults — `OPENROUTER_MODEL` in .env may still be set to flash
- Search terms: `ChatResult`, `CostBreakdown`, `get_model_for_step`, `_build_action_buttons`, `dashboard`
