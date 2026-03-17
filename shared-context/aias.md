# AI Appointment Setter (AIAS) — Project Context

## What It Does
AI-powered SMS/iMessage appointment setter evolving into a multi-tenant SaaS platform. Qualifies inbound leads, books confirmed appointments, and handles the full conversation lifecycle. Includes native CRM, pipeline management, A/B testing, and analytics dashboard.

## Stack
- **Runtime**: Express 5 (all workflows native — routes + cron jobs)
- **Messaging**: Blooio (iMessage + SMS gateway, number: +18018970049)
- **CRM**: Native CRM in Supabase (fully off GHL — no GHL dependency anywhere)
- **Database**: Supabase Postgres (Auth + RLS + Realtime) — fully migrated from Neon
- **Dashboard**: Express 5 + vanilla JS + @supabase/supabase-js at app.leadneedleai.com + app.leadneedle.com
- **LLM**: Anthropic Claude (primary) + OpenAI GPT-4.1-mini (classification/greetings)
- **Calendar**: Google Calendar API via googleapis SDK (OAuth2 refresh token)
- **Google APIs**: googleapis SDK (Sheets, Gmail, Drive, Docs, Calendar) via OAuth2 refresh token
- **Monitoring**: LeadNeedle Telegram Bot (@leadneedlebot)

## Capabilities
- **Webhook routes** (Express):
  - `/webhooks/blooio-inbound` — AI SMS pipeline
  - `/webhooks/lead-intake` — new lead processing
  - `/webhooks/booking-page` — booking form handler
  - `/webhooks/voice-agent` — ElevenLabs voice calls
  - `/webhooks/website-lead` — TFWW website lead intake + qualify
  - `/webhooks/telegram-bot` — TFWW Telegram YES/NO/NI handler
  - `/webhooks/meeting-confirm` — TFWW meeting confirmation page
- **Cron jobs** (node-cron):
  - Reminders (*/5), takeover-expiry (*/5), follow-up (*/10), monitor (*/15), timeout (daily 8am)
  - TFWW: calendar-poll (*/1), gmail-poll (*/2)
- **Services layer**: blooio, anthropic, openai, telegram, google, meta-capi
- **Lib**: country-map, phone (E.164), qualify, email-strip, tfww-state (Supabase persistence)
- Multi-tenant dashboard with auth (Supabase Auth), RLS-enforced isolation
- Native CRM: contacts, pipelines (kanban), opportunities
- A/B testing framework with variant performance tracking

## Current Status
- **LIVE**: Dashboard + TFWW at app.leadneedleai.com (TFWW_DRY_RUN=false, fully live)
- **Fully off GHL**: No GHL dependency anywhere — native CRM, native calendar, native pipeline
- **Fully off n8n**: All workflows migrated to Express routes + cron jobs
- **TFWW Dashboard**: Built (native replacement for GHL + Google Sheets)
- **TFWW API**: 4 route files at `/api/tfww/{pipeline,projects,inbox,reporting}`
- **Hostname routing**: app.leadneedleai.com → TFWW dashboard, app.leadneedle.com → AIAS dashboard
- **Supabase**: Full migration complete, Neon decommissioned

## Integration Points
- **Supabase**: https://etdeivgkcxtcsxavdjjt.supabase.co (East US / N. Virginia)
- **Blooio API**: https://backend.blooio.com/v2/api
- **Coolify**: Boston server 76.13.29.110 (dashboard hosted)
- **Telegram**: @leadneedlebot for system alerts (chat ID 6463086097)
