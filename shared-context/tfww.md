# The Free Website Wizards (TFWW) — Project Context

## What It Does
Marketing website for TFWW — a free website agency for small businesses (~300 built). Revenue from hosting affiliate commissions and future paid add-ons (not yet offered). Owned by Dylan / Lead Needle LLC.

## Stack
- **Runtime**: Static HTML/CSS/JS (no framework), Tailwind CSS v4
- **Build**: @tailwindcss/cli, Vercel (build + hosting)
- **Tracking**: GA4 (G-QWWSYRKH49) + Meta Pixel (3032047526979670)
- **Lead intake**: Cloudflare Worker → Google Sheets + GoHighLevel CRM
- **Automations**: n8n at n8n.leadneedleai.com
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
- **Needs work**: booking page has Calendly but should use AIAS text-based booking instead (see HANDOFF.md in tfww repo). Options: adapt AIAS booking page or remove booking step entirely and let AIAS text leads after form submit
- **Needs work**: stat "200+" should be "300+", acceptance rate claims need removal
- **Not live**: domain thefreewebsitewizards.com still points to old Bluehost site
- **Not connected**: Vercel not linked to GitHub repo for auto-deploys
- Add-on pricing on services page is aspirational — no paid services delivered yet

## Integration Points
- **AIAS**: AI appointment setter via Blooio/iMessage feeds same GoHighLevel pipeline
- **Mission Control**: Can monitor site status and analytics
- **n8n**: Lead routing workflows at n8n.leadneedleai.com
- **Lead intake endpoint**: https://lead-intake.dylan-2f6.workers.dev/lead-intake
- **Old site**: Bluehost cPanel SSH (rxdutbmy@thefreewebsitewizards.com:22)
