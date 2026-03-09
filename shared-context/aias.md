# AI Appointment Setter (AIAS) — Project Context

## What It Does
AI-powered SMS/iMessage appointment setter that qualifies inbound leads, books confirmed appointments via GHL Calendar, and handles the full conversation lifecycle with human-like typing indicators and reactions.

## Stack
- **Runtime**: n8n workflows (self-hosted on Coolify at n8n.leadneedleai.com)
- **Messaging**: Blooio (iMessage + SMS gateway, number: +18018970049)
- **CRM**: GoHighLevel (contacts, pipelines, calendar booking)
- **Database**: Neon Postgres (conversations, messages, follow-ups)
- **LLM**: OpenAI GPT-4.1-mini (structured output) with Anthropic fallback
- **Calendar**: GHL Calendar API (real-time free-slots), Google Calendar via gws CLI for dev

## Capabilities
- Inbound lead handling: Blooio webhook → normalize → idempotency check → qualify → respond
- Real-time calendar availability from GHL (90+ slots, 7-day window, 30-min blocks)
- Appointment booking and confirmation via GHL Calendar API
- Typing indicators (POST /typing every 4s loop), read receipts, iMessage reactions
- Timezone inference from 371 US area codes (no asking the lead)
- DNC/STOP compliance with `confused` intent for ambiguous hostility
- Follow-up nudge system with booking-aware guards (won't nudge after confirmed)
- Rapid-fire dedup (5s window prevents double-sends)
- Dry-run test mode (httpbin.org redirect) and live test mode
- Self-hosted booking page (booking-page/index.html) with webhook to Workflow 9
- Autonomous test harness (scripts/auto-test.py) for CI-style verification

## Current Status
- **Workflow 1 (Inbound)**: FUNCTIONAL — 125 nodes, all edge cases pass (7/7 scenarios)
- **Workflow 2 (Follow-Up)**: FUNCTIONAL — booking-aware, won't nudge confirmed leads
- **Workflow 6 (Reminders)**: FUNCTIONAL — skips follow-ups for booked conversations
- **Workflow 9 (Booking Page)**: FUNCTIONAL — receives booking submissions, texts lead to confirm
- **Prompt quality**: Tested and refined — no fabrication, business hours enforced, natural tone
- **GHL Calendar**: Live integration working (epoch ms timestamps, slot parser fixed)
- **Reactions**: Credential fix deployed, works on real Blooio messages (404 on synthetic test IDs)
- **Known**: CLAUDE.md has exposed API keys (legacy, needs cleanup)

## Integration Points
- **GHL**: Location `KYtt3KpkvxxWw9qsMX9v`, Sales Pipeline `Uiw8I0w5Crmg8SWPtp7G`, Calendar `JNsycZZ4HzCwvY5NJ5kA`
- **Blooio API**: https://backend.blooio.com/v2/api (send, typing, read, reactions, conversation history)
- **n8n API**: Workflow deploy, execution monitoring, credential management
- **Neon Postgres**: conversations, messages, follow_ups, scheduled_messages tables
- **Booking page webhook**: POST /webhook/booking-request → Workflow 9
- **Shared with ghl-fix**: Same GHL location, pipeline, and calendar
- **Shared with tfww**: Booking page replaces Calendly on website
