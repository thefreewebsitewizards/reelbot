# GnomeGuys — Project Context

## What It Does
Masters Tournament 2026 merch resale operation — pre-sell, source, and resell Masters merchandise (gnomes, chairs, cups, flags, etc.) via website, eBay, and airport channels. Targeting $15-25K profit over tournament week (Apr 6-12, 2026).

## Stack
- **Runtime**: Node.js (Next.js 16 / React 19) for website, Python 3 for scraper
- **Other key tech**: Shopify Storefront API (checkout/products), Tailwind CSS 4, TypeScript, Apify + Playwright (FB Marketplace scraping), Discord webhooks (alerts), SQLite (scraper dedup)

## Capabilities
- E-commerce website with product pages, Shopify checkout, pre-order flow, blog (6 SEO posts), sell-to-us page
- Facebook Marketplace monitor: Apify primary + Playwright fallback, color-coded Discord alerts by price tier
- eBay listing HTML template with pricing strategy docs
- Marketing configs: Google Ads campaigns, Facebook/IG ad targeting, SEO keyword research, ad copy variations
- Ops playbooks: airport sales scripts, buyer coordination/commissions, FB Marketplace negotiation scripts, pricing tiers across all channels
- Tracking: Meta Pixel, Google Tag Manager

## Current Status
- Initial commit landed (2026-03-07). Website scaffolded with Next.js, Shopify integration, blog content, all pages
- Scraper code complete (monitor, alerts, config, db modules)
- eBay templates and all marketing/ops docs in place
- Timeline: Week 2 (Mar 7-13) focus is website core build, product pages, checkout, first blog posts
- Pre-orders target ~Mar 25, tournament week Apr 6-12

## Sales Operation
- **Airport channel**: Working as baggage assist at local private airport (FBO), building rapport with private jet travelers, then pitching Masters merch
- **Approach**: Be their go-to guy — carry bags, be helpful, earn trust, then casually introduce gnome merch. Not hard-sell, relationship-first
- **Target audience**: High net worth individuals flying private during Masters week — they have money and want unique souvenirs
- **Reel insights**: Sales strategies from Instagram reels auto-populate into `gnomeguys/sales/reel-insights.md` for continuous improvement

## Integration Points
- **Shopify Storefront API**: product data + checkout
- **Apify API**: Facebook Marketplace scraping
- **Discord webhooks**: scraper price alerts
- **Meta Pixel + GTM**: ad tracking on website
- **Vercel**: website deployment target
