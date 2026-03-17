# The Free Website Wizards (TFWW) — Project Context

## What It Does
Marketing website for TFWW — a free website agency for small businesses (~300 built). Revenue from hosting affiliate commissions and future paid add-ons (not yet offered). Owned by Dylan / Lead Needle LLC.

## Stack
- **Runtime**: Static HTML/CSS/JS (no framework), Tailwind CSS v4
- **Build**: @tailwindcss/cli, Vercel (build + hosting)
- **Tracking**: GA4 (G-QWWSYRKH49) + Meta Pixel (3032047526979670)
- **Lead intake**: Cloudflare Worker → AIAS Express webhook → Supabase CRM
- **CRM/Dashboard**: `dashboard.thefreewebsitewizards.com` (AIAS Express, Supabase-backed)
- **Automations**: AIAS Express backend (native routes + cron jobs)
- **Repo**: https://github.com/thefreewebsitewizards/tfww-website

## Capabilities
- 8-page site: index, offer, portfolio, services, book, thank-you, privacy, terms
- Client-side A/B testing with persistent variant assignment (hero headline, CTA text)
- Multi-step lead capture modal (5 steps) with GA4 + Meta Pixel conversion tracking
- Real portfolio: 13 client showcases with optimized WebP screenshots
- Vanilla JS: scroll animations, accordion FAQ, mobile nav, sticky CTA bar

## Current Status
- Site built from scratch and deployed: https://tfww-nine.vercel.app
- Pushed to GitHub (March 2026), content verified with real clients/testimonials
- **Booking**: Uses AIAS text-based booking (not Calendly)
- **Not live**: domain thefreewebsitewizards.com still points to old Bluehost site
- **Not connected**: Vercel not linked to GitHub repo for auto-deploys
- Add-on pricing on services page is aspirational — no paid services delivered yet
- **TODO**: Advanced Meta tracking/analytics/CAPI on the site for ads

## TFWW CRM Dashboard (at AIAS Express)
- **URL**: `dashboard.thefreewebsitewizards.com`
- **Features**: Sales pipeline (kanban), fulfillment projects (kanban), unified inbox (email, soon Instagram/Facebook), contacts table, reporting charts
- **Data**: 892 contacts, 890 opportunities migrated from Google Sheets (March 2026)
- **Pipeline**: 8 stages (Inbound → Contacted → Meeting Booked → Closed Won → Onboarding → Active → Churned → Lost)
- **Inbox channels**: Email (Gmail) working. Instagram + Facebook Messenger planned
- **Webhook**: Lead form → `POST /webhooks/website-lead` → contact + opportunity + inbox_thread + Meta CAPI + Telegram notification

## Meta / Facebook Integration
- **Meta Pixel**: 3032047526979670 (on website)
- **Facebook App**: "The Free Website Wizards" (ID: 845235014725917)
- **Facebook Page**: ID 61577287178455
- **Current CAPI**: fires Lead event on webhook intake + ViewContent on meeting booked (server-side via AIAS Express)

## Web Design Knowledge Base
- `web-design/` folder in tfww repo — centralized design intelligence for autonomous web builds
- Files: design-system.md, patterns.md, principles.md, reel-insights.md

## Integration Points
- **AIAS Express**: Dashboard backend at `~/projects/openclaw/claude-code-projects/aias/dashboard/`
- **Lead intake endpoint**: https://lead-intake.dylan-2f6.workers.dev/lead-intake (Cloudflare Worker → AIAS Express webhook)
- **Supabase**: contacts, opportunities, pipeline_stages, projects, inbox_threads, inbox_messages
- **Old site**: Bluehost cPanel SSH (rxdutbmy@thefreewebsitewizards.com:22)
