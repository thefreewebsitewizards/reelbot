# Session Handoff — 2026-03-10 (Session 7)

## Project Overview
- Instagram Reel → Business Strategy Pipeline (FastAPI + Telegram bot + OpenRouter LLM)
- Ref: `CLAUDE.md` for full architecture, commands, execution rules

## Completed This Session

### 1. Shared env system
- Created `~/projects/openclaw/.shared-env/master.env` — 63 vars, organized by service category
- Sync script: `.shared-env/sync.sh [project|all|--diff|--keys|--find KEY]` (Python-based, handles special chars)
- `.shared-env/` gitignored at root level
- Fixed ghl-fix `.env` bug: `CF_API_KEY` was concatenated with `COOLIFY_API_TOKEN` on one line
- Synced all projects — `sync.sh --diff` shows clean
- Global rules updated in `~/.claude/rules/standards.md` with shared env docs

### 2. Swapped LLM to Kimi K2.5
- Changed `src/config.py:12` — `openrouter_model` from `google/gemini-2.5-pro` to `moonshotai/kimi-k2.5`
- ~75% cheaper ($0.45/$2.20 vs $1.25/$10.00 per M tokens), competitive quality (Intelligence Index 47)
- Similarity check stays on Gemini 2.5 Flash

### 3. Web design knowledge base
- Created `~/projects/openclaw/claude-code-projects/tfww/web-design/` with 4 files:
  - `design-system.md` — colors, typography, spacing (TFWW + GnomeGuys palettes)
  - `patterns.md` — animations, layouts, forms, responsive patterns
  - `principles.md` — UX rules, performance standards, branding
  - `reel-insights.md` — auto-populated by ReelBot (template, empty)
- Updated `~/.shared-context/tfww.md` to reference the knowledge base

### 4. Multi-project insight distribution system
- `src/utils/insight_distributor.py` — routes insights to ALL relevant project folders by topic
- Routing map: sales→tfww+gnomeguys, web_design→tfww, marketing→tfww+gnomeguys, ai_automation→claude-upgrades+aias, content→ddb, crm→ghl-fix, automation→n8n
- Creates sub-folders automatically (`sales/`, `web-design/`, `reel-insights/`, `marketing/`)
- Each entry contextualized for the target project's specific use case
- HANDOFF.md safe append: adds "New Reel Insights" section without overwriting
- `distributions.json` saved in each plan dir for tracking
- `src/models.py:79` — added `web_design_insights: list[str]` to AnalysisResult
- `src/prompts/analyze_reel.py` — LLM extracts web_design_insights with specific rules
- `src/prompts/generate_plan.py` — plan generator references web-design knowledge base
- `src/routers/reel.py` — hooked distributor into pipeline after write_plan

### 5. GnomeGuys context update
- Updated `~/.shared-context/gnomeguys.md` with airport sales operation details
- In-person sales at private airport FBO, baggage assist → rapport → pitch Masters merch
- Created `gnomeguys/sales/` and `tfww/sales/` folders

## Key Decisions
- Kimi K2.5 over GLM-5 (3-point quality gap not worth 2x cost for business analysis)
- Repurposing + personal brand steps kept for now (~$0.015/reel on Kimi, negligible)
- Python sync script over bash (env files have special chars that break bash string comparison)
- Insight distribution uses category→topic mapping, not per-reel LLM calls (free, deterministic)

## Priority Next Steps

### 1. Test a reel end-to-end
- Process a real reel to verify: Kimi K2.5 quality, insight distribution, web_design_insights extraction
- Check that insights land in correct project folders with proper context
- Verify `distributions.json` gets created in plan dir

### 2. Deploy to production
```bash
cd ~/projects/openclaw/claude-code-projects/reelbot
git add -A && git commit -m "feat: shared env, kimi k2.5, multi-project insight distribution"
git push origin main && git push origin main:deploy
# Restart via Coolify (see deploy commands in CLAUDE.md)
```

### 3. Consider removing repurposing + personal brand steps
- Only ~$0.015/reel savings on Kimi — low priority unless output quality is bad

### 4. Keep shared env fresh
- When rotating API keys: update `~/.shared-env/master.env` then run `sync.sh all`

## Context Notes
- `src/utils/design_insights.py` still exists but is no longer imported — can be deleted (replaced by `insight_distributor.py`)
- Pre-push hook (`.git/hooks/pre-push`) syncs shared-context files — not tracked by git
- Telegram bot token in .env has Windows line endings — always `tr -d '\r'` when extracting
- Shared context loader priority: `~/projects/openclaw/.shared-context/` → `/app/shared-context/` → `./shared-context/`
