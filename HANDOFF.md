# Session Handoff — 2026-03-16 (Session 17)

## Project Overview
- Instagram Reel -> Business Strategy Pipeline (FastAPI + Telegram + OpenRouter LLM)
- Ref: `CLAUDE.md` for full architecture, commands, execution rules

## Completed This Session

### Ops cleanup from session 16's next steps
- [x] Deployed agent loop to VPS (`reelbot-agent.service` on 217.216.90.203, polling every 60s)
- [x] Verified Telegram webhook is clear (polling mode works)
- [x] Deleted 2 stale plans (pre-control-panel, never approved, OpenClaw/Julian Goldie content)
- [x] Updated `~/.shared-context/reelbot.md` with web control panel, simplified Telegram
- [x] Saved VPS SSH access details to memory (`reference_vps_access.md`)

### Reliability + code quality improvements (commit `064d03d`)
- **CORS restriction**: `allow_origins=["*"]` → env-configurable (`CORS_ORIGINS`), defaults to production domain
- **Health endpoints**: `/health` (liveness) + `/ready` (checks plans dir, env vars, ffmpeg)
- **Constants**: `src/constants.py` — all magic numbers centralized (timeouts, retries, limits)
- **Retry utility**: `src/utils/retry.py` — exponential backoff with jitter, applied to LLM calls + n8n webhook
- **File splits** (all under 300 lines now):
  - `plan_writer.py` (638→294) + `html_renderer.py` (236) + `plan_formatter.py` (79)
  - `executor.py` (406→258) + `tool_handlers.py` (154)
  - `telegram_bot.py` (507→87) + `telegram_handlers.py` (270) + `telegram_similarity.py` (217)
- **Route tests**: 14 new tests (health, plans CRUD, auth, reel processing). Total: 75 tests passing

### Design: Similarity + Plan View Redesign
- Full design doc at `docs/plans/2026-03-16-similarity-planview-redesign.md`
- User approved design, not yet implemented

## Next Steps

- [ ] **Implement similarity + plan view redesign** — the approved design doc covers everything:
  1. Enrich similarity check to load actual plan.md content and produce per-area comparisons (`src/services/planner.py`, `src/models.py`)
  2. Add `ContentComparison` model with verdict (better/worse/same/different_angle) + `ContentResponse` for social media plays
  3. Feed comparison context into planner prompt, add `change_type` to tasks (addition/replacement/reinforcement/ignore)
  4. Restructure HTML: nav bar + section jump links, reorder (applications + levels before tasks), new "Comparison to Current State" and "Social Media Play" sections, remove bloat (swipe phrases, standalone DDB angle)
  5. Update Telegram similarity message with actual comparison details
  6. Update tests for new model fields
- [ ] **Test the full flow** — send a reel, verify: Telegram notification → web control panel → approve → execution

## Key Decisions
- Pull actual plan.md content for similarity comparisons (quality over token cost)
- Social media section is a proper section (react/correct/repurpose), not just a one-liner
- L3 task splitting preserved (user liked cherry-picking individual L3 tasks)
- Swipe phrases section removed (rarely populated, not actionable)
- DDB content angle folded into social media section or L3 tasks

## Context Notes
- `approval_notes` saved in metadata.json but not yet read by executor
- `_handle_generate_anyway` in `telegram_similarity.py` loads analysis from disk and generates plan
- The approve endpoint auto-triggers execution in a background thread
- Re-exports in split files maintain backward compatibility (tests still patch original module paths)
- `CORS_ORIGINS` env var not yet added to production .env (uses default which is correct for prod)
