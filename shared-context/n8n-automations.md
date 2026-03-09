# n8n Automations — Project Context

## What It Does
Central automation hub running 6+ workflows on n8n.leadneedleai.com. Handles lead intake, Telegram bot integrations, email processing, opportunity stage management, calendar sync, and bidirectional GHL↔Sheets sync.

## Stack
- **Runtime**: n8n (self-hosted on Coolify)
- **Integrations**: GHL API, Google Sheets API, Telegram API, email (IMAP)
- **Database**: Neon Postgres for workflow state

## Active Workflows
1. **Lead Intake** (Workflow 1) — Blooio webhook → qualify → GHL → LLM → respond
2. **Telegram Bot** — Notifications and commands
3. **Email → Client Docs** (Workflow 5) — Parse emails into client documentation
4. **Opportunity Stage** — Pipeline stage management
5. **Calendar Sync** — Appointment management
6. **GHL ↔ Sheets Sync** (Workflow 6) — Bidirectional contact sync with pagination + caching

## Capabilities
- Webhook-driven event processing
- API integrations (GHL, Sheets, Telegram, Blooio)
- LLM-powered message parsing (OpenAI structured output)
- Cursor-based pagination for large datasets
- Contact ID caching for performance
- Rate-limited batch operations

## Current Status
- All 6 workflows active and deployed
- 852/852 tests passing
- GHL↔Sheets sync has pagination + contact ID cache
- Phone E164 normalization fixed (double country code issue)
