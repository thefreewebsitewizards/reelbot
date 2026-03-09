# GHL Fix — Project Context

## What It Does
Manages 6 N8N workflows on `n8n.leadneedleai.com` that handle lead intake, CRM automation, and bidirectional GHL-Sheets sync for The Free Website Wizards.

## Stack
- **Runtime**: Node.js (ESM), N8N workflow engine
- **APIs**: GoHighLevel (PIT token), N8N REST API (behind Cloudflare Access), Google Sheets OAuth2, Gmail OAuth2, Telegram Bot API, Meta CAPI
- **Testing**: Custom structural test suite (852 tests, 12 suites)

## Capabilities
- **Workflow 1** (Lead Intake + Qualify): POST webhook `/webhook/lead-intake` → normalize fields, E.164 phone formatting, GHL contact upsert + opportunity creation, Sheets backup, Telegram + Gmail notifications
- **Workflow 2** (Telegram Bot): Callback-driven contact status updates (Called YES/NO/NI) → GHL tags + Sheets updates
- **Workflow 3** (Meta CAPI / Opp Stage): Opportunity stage changes → Meta Conversion API events, client sheet management
- **Workflow 4** (Calendar): Meeting booked/confirmed events → GHL opportunity updates, Sheets status tracking
- **Workflow 5** (Email → Client Doc): Gmail trigger → email thread stripping → GHL document storage, client folder management
- **Workflow 6** (GHL ↔ Sheets Sync): 5-min schedule, bidirectional — GHL→Sheets: phone/name (paginated, 1000 contacts/cycle), Sheets→GHL: Called?/Notes (hash-based change detection, contactId cache)
- **Scripts**: `upload-workflows.js` (validate/upload/activate), `test-workflows.js` (852 structural tests), `check-exec.js` / `check-email-exec.js` (execution inspectors), `clean-test-contacts.js` (test data cleanup)

## Current Status
- All 6 workflows deployed and active on N8N server
- 852/852 tests passing
- Email thread stripping deployed but not yet triggered by a qualifying email
- Shared GHL location `KYtt3KpkvxxWw9qsMX9v` and pipeline `Uiw8I0w5Crmg8SWPtp7G` with AIAS project — concurrent contact/opp writes possible
- Calendly being dropped from ad funnel (AIAS built replacement); TFWW website still uses Calendly and needs migration
- Calendar unification planned: one Google Calendar as source of truth, GHL two-way sync
- Old Blooio webhook to `thefreewebsitewizards.app.n8n.cloud` deleted — only `n8n.leadneedleai.com` receives events now

## Integration Points
- **GHL Location**: `KYtt3KpkvxxWw9qsMX9v` — contacts, opportunities, custom fields (shared with AIAS)
- **GHL Pipeline**: `Uiw8I0w5Crmg8SWPtp7G` — stages: Inbound, Meeting Booked, Closed Won
- **GHL Calendar**: `JNsycZZ4HzCwvY5NJ5kA` (shared with AIAS for free-slots API)
- **Google Sheets**: Submissions `1batVITcT526zxkc8Qdf0_AKbORnrLRB7-wHdDKhcm9M`, Clients `1-1XxiMGvGhiQQZvBv1ze7Pf6TZmW3FsGGDv6SgcmBro`
- **N8N Server**: `n8n.leadneedleai.com` (Cloudflare Access protected)
- **Webhook**: `POST /webhook/lead-intake` on N8N server
- **Note**: AIAS writes conversation state to Neon Postgres, separate from ghl-fix's Sheets sync
