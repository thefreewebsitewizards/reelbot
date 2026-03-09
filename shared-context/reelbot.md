# ReelBot — Project Context

## What It Does
Instagram Reel → Business Strategy Pipeline. Receives reel URLs via Telegram bot or API, downloads video, transcribes audio, analyzes with Claude for business insights, generates implementation plans with concrete tasks.

## Stack
- **Runtime**: Python 3.11, FastAPI, uvicorn
- **LLM**: OpenRouter (Claude models) for analysis + planning
- **Bot**: Telegram bot for reel submission and plan review
- **Hosting**: Coolify on VPS (76.13.29.110)
- **Storage**: Local filesystem (plans/ directory with JSON metadata + HTML views)

## Capabilities
- Video download + audio extraction (yt-dlp, ffmpeg)
- Whisper transcription (via API)
- Vision analysis (keyframe extraction + Claude vision)
- Carousel/image post analysis (OCR + vision)
- Plan generation with cost tracking
- Telegram interactive feedback (rate plans good/bad/partial)
- Similarity detection between new reels and existing plans
- Web dashboard for viewing plans

## Current Status
- **Deployed and running** on production
- Pipeline: reel URL → download → transcribe → analyze → plan → Telegram notification
- Prompt system recently overhauled for better business context accuracy
- Feedback/training calibration in progress

## API Endpoints
- POST /api/reel — Submit reel URL for processing
- GET /api/plans — List all plans
- GET /api/plans/{id} — View specific plan
- GET /health — Health check
- GET /dashboard — Web dashboard
